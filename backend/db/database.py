"""数据库会话管理（自动创建 sqlite 数据目录）"""
from pathlib import Path

from config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_engine():
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        db_path = url.split("///", 1)[-1]
        if db_path and not db_path.startswith(":"):
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False}, echo=False)
    return create_engine(url, pool_pre_ping=True, echo=False)


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models.database import Base
    Base.metadata.create_all(bind=engine)
