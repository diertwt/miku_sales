# подключение, создание таблиц

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils.paths import DB_PATH
from core.models import Base

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db() -> None:
    """Создаёт таблицы, если их нет."""
    Base.metadata.create_all(engine)