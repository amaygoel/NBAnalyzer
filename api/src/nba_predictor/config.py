import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://localhost:5432/nba_predictor"
    )
    # For local development, can use SQLite instead
    USE_SQLITE: bool = os.getenv("USE_SQLITE", "true").lower() == "true"
    SQLITE_URL: str = "sqlite:///nba_predictor.db"

    @property
    def db_url(self) -> str:
        if self.USE_SQLITE:
            return self.SQLITE_URL
        return self.DATABASE_URL


settings = Settings()
