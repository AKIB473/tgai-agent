"""
security/permissions.py — Permission system.

Levels:
  - BANNED:  Blocked from all interaction
  - USER:    Standard user; can use AI and configure own chats
  - ADMIN:   Full system access; can manage users, view logs, etc.
"""

from __future__ import annotations

from enum import IntEnum

from tgai_agent.config import settings
from tgai_agent.storage.repositories.user_repo import get_user, is_banned
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


class PermissionLevel(IntEnum):
    BANNED = -1
    USER = 0
    ADMIN = 10


async def get_permission_level(user_id: int) -> PermissionLevel:
    if user_id in settings.admin_ids:
        return PermissionLevel.ADMIN

    if await is_banned(user_id):
        return PermissionLevel.BANNED

    user = await get_user(user_id)
    if user and user.get("is_admin"):
        return PermissionLevel.ADMIN

    return PermissionLevel.USER


async def require_permission(user_id: int, level: PermissionLevel = PermissionLevel.USER) -> bool:
    """
    Returns True if user has at least `level` permission.
    Should be called at the top of every command handler.
    """
    actual = await get_permission_level(user_id)
    if actual == PermissionLevel.BANNED:
        log.warning("permissions.banned_access_attempt", user_id=user_id)
        return False
    return actual >= level


async def is_admin(user_id: int) -> bool:
    return await get_permission_level(user_id) >= PermissionLevel.ADMIN
