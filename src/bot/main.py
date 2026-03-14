"""Bot entry point: aiogram polling + optional automation HTTP server."""
import asyncio
import logging
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bot.admin import router as admin_router
from src.bot.handlers.ai_chat import router as ai_chat_router
from src.bot.handlers.start import router as start_router
from src.bot.handlers.verification import router as verification_router
from src.bot.navigation import router as navigation_router
from src.bot.middlewares.ai_inject import InjectAIMiddleware
from src.bot.middlewares.log_updates import LogUpdatesMiddleware
from src.bot.middlewares.admin_middleware import AdminOnlyMiddleware
from src.config import get_settings
from src.core.services.ai.ai_courier_service import AICourierService
from src.core.services.ai.ai_facade import AIFacade
from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.ai.providers.deepseek_provider import DeepSeekProvider
from src.core.services.ai.providers.groq_provider import GroqProvider
from src.core.services.ai.providers.openai_compatible_provider import (
    OpenAICompatibleProvider,
)
from src.core.services.ai.providers.openai_provider import OpenAIProvider
from src.core.services.access_service import AccessService
from src.core.services.ingest import IngestService
from src.core.services.users import UserService
from src.core.services.verification_service import VerificationService
from src.api.automation import create_automation_app
from src.core.events import EventBus
from src.core.proactive_layer import register_proactive_handlers
from src.infra.db.repositories.faq_repo import FAQRepository
from src.infra.db.session import async_session_factory

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _init_ai(dp: Dispatcher) -> None:
    """Initialize AI services and store them on the dispatcher (Bot has no .get/[])."""
    settings = get_settings()
    dp["ai_router"] = None
    dp["provider_router"] = None
    dp["ai_service"] = None
    dp["ai_facade"] = None
    dp["faq_repo"] = FAQRepository()

    if not settings.ai_enabled:
        logger.info("AI disabled (AI_ENABLED=false)")
        return

    # Log canonical embedding backend once at startup (provider + model)
    from src.core.services.ai.embedding_service import get_embedding_service

    _embedding_svc = get_embedding_service()
    logger.info(
        "active_embedding_backend: provider=%s model=%s enabled=%s",
        _embedding_svc.provider,
        _embedding_svc.model,
        _embedding_svc.enabled,
    )

    ai_router = ProviderRouter(
        [
            GroqProvider(),
            DeepSeekProvider(),
            OpenAIProvider(),
            OpenAICompatibleProvider(),
        ]
    )
    ai_service = AICourierService(
        session_factory=async_session_factory,
        router=ai_router,
    )
    ai_facade = AIFacade(_courier=ai_service, _router=ai_router, _data_root="data/ai")

    dp["ai_router"] = ai_router
    dp["provider_router"] = ai_router
    dp["ai_service"] = ai_service
    dp["ai_facade"] = ai_facade
    enabled_providers = sorted(ai_router.providers.keys())
    if enabled_providers:
        logger.info("AI initialized: providers=%s", enabled_providers)
    else:
        logger.warning(
            "AI initialized with zero enabled providers; LLM calls will use fallback"
        )


async def _shutdown_ai(bot: Bot, dp: Dispatcher) -> None:
    ai_router = dp.get("ai_router")
    if ai_router:
        await ai_router.close()
        logger.info("AI providers closed")


def _register_error_handler(dp: Dispatcher) -> None:
    from aiogram import Router
    from aiogram.types import ErrorEvent

    err_router = Router(name="errors")

    @err_router.error()
    async def _on_error(event: ErrorEvent) -> None:
        logger.exception("handler_error: %s", event.exception)
        msg = event.update.message if event.update else None
        if msg and hasattr(msg, "answer"):
            try:
                await msg.answer("Произошла ошибка. Попробуйте позже или напишите /start.")
            except Exception:
                pass

    dp.include_router(err_router)


async def main() -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set")
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    # Без сброса webhook long polling не получает обновления
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook cleared for polling")
    except Exception as e:
        logger.warning("delete_webhook: %s", e)

    dp = Dispatcher()
    dp["event_bus"] = EventBus()
    register_proactive_handlers(
        dp["event_bus"],
        async_session_factory,
        bot=bot,
        access_service=dp["access_service"],
    )
    dp["user_service"] = UserService(session_factory=async_session_factory)
    dp["access_service"] = AccessService(
        session_factory=async_session_factory,
        settings=settings,
    )
    dp["verification_service"] = VerificationService(session_factory=async_session_factory)
    dp["ingest_service"] = IngestService()
    dp.update.outer_middleware(LogUpdatesMiddleware())
    dp.update.outer_middleware(InjectAIMiddleware(dp))
    dp.update.outer_middleware(AdminOnlyMiddleware(dp))
    _init_ai(dp)

    dp.include_router(start_router)
    dp.include_router(navigation_router)
    dp.include_router(admin_router)
    dp.include_router(verification_router)
    dp.include_router(ai_chat_router)  # last: catches free text after commands
    _register_error_handler(dp)

    async def _on_shutdown(bot: Bot) -> None:
        await _shutdown_ai(bot, dp)

    dp.shutdown.register(_on_shutdown)

    # Optional: HTTP server for POST /automation/event (n8n automation)
    automation_port = getattr(settings, "automation_http_port", 0) or 0
    if automation_port > 0:
        automation_app = create_automation_app(dp)
        runner = web.AppRunner(automation_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", automation_port)
        await site.start()
        logger.info("automation_http_listen", port=automation_port)

        async def _cleanup_automation(_bot: Bot) -> None:
            await runner.cleanup()

        dp.shutdown.register(_cleanup_automation)

    await dp.start_polling(bot)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
