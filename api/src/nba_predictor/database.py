from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from nba_predictor.config import settings


engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False} if settings.USE_SQLITE else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
