from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker,Session
from collections.abc import Generator

DATABASE_URL = "sqlite:///slms.db"

class Base(DeclarativeBase):
    pass

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


SessionLocal = sessionmaker(
    autocommit =  False,
    autoflush =  False,
    bind = engine
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

