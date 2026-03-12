from aiogram import Router

from src.bot.admin.admin_handlers import router as admin_menu_router
from src.bot.admin.ai_admin import router as ai_admin_router
from src.bot.admin.incident import router as incident_router
from src.bot.admin.ingest import router as ingest_router
from src.bot.admin.tmc_issue import router as tmc_router


router = Router(name="admin")
router.include_router(admin_menu_router)
router.include_router(tmc_router)
router.include_router(incident_router)
router.include_router(ingest_router)
router.include_router(ai_admin_router)

