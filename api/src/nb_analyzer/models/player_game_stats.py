from sqlalchemy import Integer, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nb_analyzer.database import Base


class PlayerGameStats(Base):
    __tablename__ = "player_game_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="uq_player_game"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)  # Team player was on for this game

    # Playing time
    minutes: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Basic stats
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rebounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offensive_rebounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    defensive_rebounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnovers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    personal_fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Shooting
    fg_made: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fg_attempted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    three_made: Mapped[int | None] = mapped_column(Integer, nullable=True)
    three_attempted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ft_made: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ft_attempted: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Advanced
    plus_minus: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Whether player started the game
    started: Mapped[bool | None] = mapped_column(Integer, nullable=True)  # Using int for SQLite compatibility

    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="game_stats")
    game: Mapped["Game"] = relationship("Game", back_populates="player_stats")

    @property
    def pra(self) -> int | None:
        """Points + Rebounds + Assists"""
        if self.points is None or self.rebounds is None or self.assists is None:
            return None
        return self.points + self.rebounds + self.assists

    def __repr__(self) -> str:
        return f"<PlayerGameStats {self.player_id} in game {self.game_id}: {self.points}pts>"
