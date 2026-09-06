"""管理员一次性引导（M4.6 R-C6）：仅空表时生效，凭据来自环境变量。"""

from config import settings
from core.logging import get_logger
from core.security import hash_password
from db.database import SessionLocal
from models.database import User

logger = get_logger()


def _create_admin_if_empty(db) -> None:
    username = (settings.ADMIN_BOOTSTRAP_USERNAME or "").strip()
    password = settings.ADMIN_BOOTSTRAP_PASSWORD or ""
    if not username or not password:
        return
    if db.query(User).count() > 0:
        logger.info("admin_bootstrap_skipped", extra={"reason": "users_table_not_empty"})
        return
    user = User(
        username=username,
        password_hash=hash_password(password),
        nickname=username,
        is_admin=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("admin_bootstrap_created", extra={"user_id": user.id})


def bootstrap_admin_if_configured() -> None:
    """启动时调用：配置了 ADMIN_BOOTSTRAP_* 且 users 空表时创建 admin。"""
    db = SessionLocal()
    try:
        _create_admin_if_empty(db)
    finally:
        db.close()
