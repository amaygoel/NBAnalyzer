from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nba_predictor.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # NBA team ID
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Golden State Warriors"
    abbreviation: Mapped[str] = mapped_column(String(3), nullable=False)  # e.g., "GSW"
    city: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "Golden State"
    conference: Mapped[str] = mapped_column(String(10), nullable=False)  # "East" or "West"
    division: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "Pacific"

    # Relationships
    players: Mapped[list["Player"]] = relationship("Player", back_populates="team")
    home_games: Mapped[list["Game"]] = relationship(
        "Game", foreign_keys="Game.home_team_id", back_populates="home_team"
    )
    away_games: Mapped[list["Game"]] = relationship(
        "Game", foreign_keys="Game.away_team_id", back_populates="away_team"
    )

    def __repr__(self) -> str:
        return f"<Team {self.abbreviation}: {self.name}>"
