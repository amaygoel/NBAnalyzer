"""
Add game_time column to games table.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nb_analyzer.database import SessionLocal, engine
from sqlalchemy import text


def add_game_time_column():
    """Add game_time column to games table."""
    db = SessionLocal()

    try:
        # Check if column already exists
        result = db.execute(text("PRAGMA table_info(games)"))
        columns = [row[1] for row in result]

        if 'game_time' in columns:
            print("✓ game_time column already exists")
            return

        # Add the column
        print("Adding game_time column to games table...")
        db.execute(text("ALTER TABLE games ADD COLUMN game_time DATETIME"))
        db.commit()
        print("✅ Successfully added game_time column")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_game_time_column()
