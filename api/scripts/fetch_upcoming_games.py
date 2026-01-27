"""
Fetch upcoming games for the next 14 days from the NBA API.
This ensures the weekly view always has games available.
Runs daily via cron.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fetch_todays_games import fetch_todays_games


def fetch_upcoming_games():
    """Fetch games for the next 14 days."""
    print("=" * 60)
    print("Fetching upcoming NBA games (next 14 days)")
    print("=" * 60)

    total_added = 0
    total_updated = 0

    for days_ahead in range(14):
        game_date = date.today() + timedelta(days=days_ahead)

        try:
            print(f"\n📅 {game_date.strftime('%A, %B %d, %Y')}")
            print("-" * 60)

            # Capture output to count adds/updates
            import io
            import contextlib

            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                fetch_todays_games(game_date)

            output = f.getvalue()
            print(output, end='')

            # Parse results
            if "Added" in output:
                line = [l for l in output.split('\n') if 'Added' in l and 'new games' in l]
                if line:
                    parts = line[0].split()
                    added = int(parts[1])
                    updated = int(parts[5])
                    total_added += added
                    total_updated += updated

        except Exception as e:
            print(f"❌ Error fetching {game_date}: {e}")
            continue

    print("\n" + "=" * 60)
    print(f"✅ Fetch complete!")
    print(f"   Added: {total_added} new games")
    print(f"   Updated: {total_updated} existing games")
    print("=" * 60)


if __name__ == "__main__":
    fetch_upcoming_games()
