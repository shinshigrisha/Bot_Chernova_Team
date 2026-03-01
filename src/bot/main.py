"""Bot entry point: aiogram polling."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bot.admin import router as admin_router
from src.bot.handlers.ai_chat import router as ai_chat_router
from src.bot.handlers.start import router as start_router
from src.bot.middlewares.ai_inject import InjectAIMiddleware
from src.config import get_settings
from src.core.services.ai.ai_courier_service import AICourierService
from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.ai.providers.deepseek_provider import DeepSeekProvider
from src.core.services.ai.providers.groq_provider import GroqProvider
from src.core.services.ai.providers.openai_provider import OpenAIProvider
from src.infra.db.repositories.faq_ai import FAQAIRepository
from src.infra.db.session import async_session_factory

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _init_ai(bot: Bot) -> None:
    settings = get_settings()
    if not settings.ai_enabled:
        logger.info("AI disabled (AI_ENABLED=false)")
        return

    providers = []
    if settings.groq_api_key:
        providers.append(GroqProvider())
    if settings.deepseek_api_key:
        providers.append(DeepSeekProvider())
    if settings.openai_api_key:
        providers.append(OpenAIProvider())

    if not providers:
        logger.warning("AI_ENABLED=true but no API keys configured")
        return

    ai_router = ProviderRouter(providers)
    ai_service = AICourierService(
        session_factory=async_session_factory,
        router=ai_router,
    )

    bot["ai_router"] = ai_router
    bot["provider_router"] = ai_router
    bot["ai_service"] = ai_service
    bot["faq_repo"] = FAQAIRepository()
    logger.info("AI initialized: providers=%s", list(ai_router.providers.keys()))


async def _shutdown_ai(bot: Bot) -> None:
    ai_router = bot.get("ai_router")
    if ai_router:
        await ai_router.close()
        logger.info("AI providers closed")


async def main() -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set")
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    _init_ai(bot)

    dp = Dispatcher()
    dp.update.middleware(InjectAIMiddleware())
    if bot.get("ai_service") is not None:
        dp["ai_service"] = bot["ai_service"]
    if bot.get("ai_router") is not None:
        dp["ai_router"] = bot["ai_router"]

    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(ai_chat_router)  # last: catches free text after commands
    dp.shutdown.register(_shutdown_ai)
    await dp.start_polling(bot)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
