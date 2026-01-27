from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nb_analyzer.database import Base


class GameOdds(Base):
    """Betting odds for NBA games from various bookmakers."""
    __tablename__ = "game_odds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)

    # Bookmaker info
    bookmaker: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "draftkings"

    # Market type
    market_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "spreads", "totals", "h2h"

    # Home team odds/line
    home_line: Mapped[float | None] = mapped_column(Float, nullable=True)  # spread: -6.5, total: 220.5
    home_odds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # American odds: -110

    # Away team odds/line
    away_line: Mapped[float | None] = mapped_column(Float, nullable=True)  # spread: +6.5
    away_odds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # American odds: -110

    # For totals
    over_line: Mapped[float | None] = mapped_column(Float, nullable=True)  # 220.5
    over_odds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # -110
    under_line: Mapped[float | None] = mapped_column(Float, nullable=True)  # 220.5
    under_odds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # -110

    # Timestamp
    last_update: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationship
    game: Mapped["Game"] = relationship("Game", back_populates="odds")

    # Index for faster queries
    __table_args__ = (
        Index("idx_game_bookmaker_market", "game_id", "bookmaker", "market_type"),
    )

    def __repr__(self) -> str:
        return f"<GameOdds {self.bookmaker} - Game {self.game_id} - {self.market_type}>"
