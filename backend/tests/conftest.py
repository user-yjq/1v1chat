"""测试公共夹具：内存 sqlite + 会话"""
import pytest
from models.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class FakeLLM:
    def __init__(self, text: str = "哈喽呀，在的在的～"):
        self.text = text

    async def generate(self, system: str, user: str) -> str:
        return self.text
