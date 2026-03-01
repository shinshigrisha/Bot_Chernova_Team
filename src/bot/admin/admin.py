import os
from aiogram.types import Message

def is_admin_user(user_id: int) -> bool:
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return False
    try:
        return int(raw) == int(user_id)
    except ValueError:
        return False

async def require_admin(message: Message) -> bool:
    if not is_admin_user(message.from_user.id):
        await message.answer("Нет доступа.")
        return False
    return True