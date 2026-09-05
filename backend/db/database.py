"""数据库会话管理（自动创建 sqlite 数据目录）

- SQLite 开发库启用 WAL + busy_timeout（与 02 ADR-07 声明一致）；
  :memory:（测试）不启用文件级 PRAGMA。
- 生产候选：DATABASE_URL 切 PostgreSQL 后走同一 make_engine（pool_pre_ping）。
"""
from pathlib import Path

from config import settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()


def make_engine(url: str):
    if url.startswith("sqlite"):
        db_path = url.split("///", 1)[-1]
        if db_path and not db_path.startswith(":"):
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args={"check_same_thread": False}, echo=False)
        # 仅文件型 SQLite 启用 WAL；:memory: 跳过（无文件可持久化）
        if "///" in url and not url.endswith(":memory:"):
            event.listen(engine, "connect", _apply_sqlite_pragmas)
        return engine
    return create_engine(url, pool_pre_ping=True, echo=False)


engine = make_engine(settings.DATABASE_URL)
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
