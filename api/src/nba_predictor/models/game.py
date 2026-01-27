from datetime import date
from sqlalchemy import String, Integer, Date, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nba_predictor.database import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # NBA game ID
    date: Mapped[date] = mapped_column(Date, nullable=False)
    season: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "2023-24"

    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)

    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Calculated fields for analysis
    home_rest_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_rest_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_home_back_to_back: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_away_back_to_back: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Game status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    home_team: Mapped["Team"] = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team: Mapped["Team"] = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    player_stats: Mapped[list["PlayerGameStats"]] = relationship("PlayerGameStats", back_populates="game")

    @property
    def winner_id(self) -> int | None:
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_team_id if self.home_score > self.away_score else self.away_team_id

    @property
    def home_win(self) -> bool | None:
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score > self.away_score

    def __repr__(self) -> str:
        return f"<Game {self.id}: {self.away_team_id} @ {self.home_team_id} on {self.date}>"
