from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nba_predictor.database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # NBA player ID
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    position: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g., "Guard", "Forward"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="players")
    game_stats: Mapped[list["PlayerGameStats"]] = relationship(
        "PlayerGameStats", back_populates="player"
    )

    def __repr__(self) -> str:
        return f"<Player {self.id}: {self.name}>"
