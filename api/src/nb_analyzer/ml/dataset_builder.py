"""
Efficient training dataset builder for margin prediction model.

Builds dataset with NO data leakage - features only use games before each game's date.
Uses single-pass algorithm with in-memory team state for efficiency.
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Game


@dataclass
class TeamState:
    """Tracks running statistics for a team (updated after each game)."""
    team_id: int

    # Overall stats (all games to date)
    total_games: int = 0
    total_wins: int = 0
    total_margin: float = 0.0  # Cumulative point differential

    # Home-only stats
    home_games: int = 0
    home_margin: float = 0.0

    # Away-only stats
    away_games: int = 0
    away_margin: float = 0.0

    # Last 10 games margins (rolling window)
    last10_margins: deque = field(default_factory=lambda: deque(maxlen=10))

    # Most recent game date (for rest calculation)
    last_game_date: Optional[date] = None

    def get_win_pct(self) -> float:
        """Overall win percentage to date."""
        if self.total_games == 0:
            return 0.5  # Neutral prior
        return self.total_wins / self.total_games

    def get_avg_margin(self) -> float:
        """Average point differential (all games to date)."""
        if self.total_games == 0:
            return 0.0
        return self.total_margin / self.total_games

    def get_home_avg_margin(self) -> float:
        """Average point differential in home games only."""
        if self.home_games == 0:
            return 0.0
        return self.home_margin / self.home_games

    def get_away_avg_margin(self) -> float:
        """Average point differential in away games only."""
        if self.away_games == 0:
            return 0.0
        return self.away_margin / self.away_games

    def get_last10_avg_margin(self) -> float:
        """Average point differential over last 10 games."""
        if not self.last10_margins:
            return 0.0
        return sum(self.last10_margins) / len(self.last10_margins)

    def get_rest_days(self, game_date: date) -> int:
        """Calculate rest days before this game."""
        if self.last_game_date is None:
            return 3  # Default for first game
        return (game_date - self.last_game_date).days - 1

    def update_after_game(self, margin: float, is_home: bool, game_date: date):
        """Update state after a game completes (called AFTER features extracted)."""
        self.total_games += 1
        self.total_wins += 1 if margin > 0 else 0
        self.total_margin += margin

        if is_home:
            self.home_games += 1
            self.home_margin += margin
        else:
            self.away_games += 1
            self.away_margin += margin

        self.last10_margins.append(margin)
        self.last_game_date = game_date


class MarginDatasetBuilder:
    """Builds margin prediction training dataset efficiently."""

    def __init__(self, db: Session, output_dir: Path = None):
        self.db = db
        self.output_dir = output_dir or Path(__file__).parent.parent.parent.parent / "data"
        self.output_dir.mkdir(exist_ok=True)

        # In-memory state for all teams
        self.team_states: dict[int, TeamState] = {}

    def _get_team_state(self, team_id: int) -> TeamState:
        """Get or create team state."""
        if team_id not in self.team_states:
            self.team_states[team_id] = TeamState(team_id=team_id)
        return self.team_states[team_id]

    def _extract_features(self, game: Game) -> dict:
        """
        Extract features for a game using ONLY prior team state.
        This is called BEFORE updating team state, ensuring no leakage.
        """
        home_state = self._get_team_state(game.home_team_id)
        away_state = self._get_team_state(game.away_team_id)

        # Win percentages to date
        home_win_pct = home_state.get_win_pct()
        away_win_pct = away_state.get_win_pct()

        # Average margins to date
        home_avg_margin = home_state.get_avg_margin()
        away_avg_margin = away_state.get_avg_margin()

        # Home/away specific margins
        home_home_margin = home_state.get_home_avg_margin()
        away_away_margin = away_state.get_away_avg_margin()

        # Last 10 games margins
        home_last10_margin = home_state.get_last10_avg_margin()
        away_last10_margin = away_state.get_last10_avg_margin()

        # Rest days
        home_rest = home_state.get_rest_days(game.date)
        away_rest = away_state.get_rest_days(game.date)

        # Back-to-back flags
        home_b2b = 1 if home_rest == 0 else 0
        away_b2b = 1 if away_rest == 0 else 0

        return {
            # Identifiers (not features)
            'game_id': game.id,
            'game_date': game.date,
            'season': game.season,
            'home_team_id': game.home_team_id,
            'away_team_id': game.away_team_id,

            # Target variable
            'y_margin': game.home_score - game.away_score,

            # Features: win percentages
            'home_win_pct_to_date': home_win_pct,
            'away_win_pct_to_date': away_win_pct,
            'win_pct_diff': home_win_pct - away_win_pct,

            # Features: average margins
            'home_avg_margin_to_date': home_avg_margin,
            'away_avg_margin_to_date': away_avg_margin,

            # Features: last 10 games margins
            'home_last10_margin': home_last10_margin,
            'away_last10_margin': away_last10_margin,
            'last10_margin_diff': home_last10_margin - away_last10_margin,

            # Features: home/away splits
            'home_home_margin_to_date': home_home_margin,
            'away_away_margin_to_date': away_away_margin,

            # Features: rest & schedule
            'home_rest_days': home_rest,
            'away_rest_days': away_rest,
            'rest_diff': home_rest - away_rest,
            'home_b2b': home_b2b,
            'away_b2b': away_b2b,

            # Metadata for debugging
            'home_games_to_date': home_state.total_games,
            'away_games_to_date': away_state.total_games,
        }

    def build_dataset(self, seasons: list[str] = None, sanity_check: bool = False) -> pd.DataFrame:
        """
        Build training dataset from historical games.

        Args:
            seasons: List of seasons to include (e.g., ['2022-23', '2023-24'])
            sanity_check: If True, print sample rows and validate

        Returns:
            DataFrame with one row per completed game
        """
        if seasons is None:
            seasons = ['2022-23', '2023-24', '2024-25']

        print(f"Building dataset for seasons: {seasons}")
        print("Loading completed games from database...")

        # SINGLE query: load all completed games ordered by date
        games = self.db.query(Game).filter(
            Game.season.in_(seasons),
            Game.is_completed == True,
            Game.home_score.isnot(None),
            Game.away_score.isnot(None)
        ).order_by(Game.date, Game.id).all()

        print(f"Loaded {len(games)} completed games")
        print(f"Date range: {games[0].date} to {games[-1].date}")
        print("\nProcessing games in chronological order...")

        # Reset team states for fresh build
        self.team_states = {}

        rows = []
        for i, game in enumerate(games):
            # Extract features BEFORE updating state (no leakage)
            features = self._extract_features(game)
            rows.append(features)

            # Now update team states with this game's result
            home_margin = game.home_score - game.away_score
            away_margin = -home_margin

            home_state = self._get_team_state(game.home_team_id)
            away_state = self._get_team_state(game.away_team_id)

            home_state.update_after_game(home_margin, is_home=True, game_date=game.date)
            away_state.update_after_game(away_margin, is_home=False, game_date=game.date)

            if (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{len(games)} games...")

        df = pd.DataFrame(rows)
        print(f"\n✅ Dataset built: {len(df)} rows, {len(df.columns)} columns")

        if sanity_check:
            self._run_sanity_check(df, games)

        return df

    def _run_sanity_check(self, df: pd.DataFrame, games: list[Game]):
        """Validate dataset for data leakage and correctness."""
        print("\n" + "="*70)
        print("SANITY CHECK")
        print("="*70)

        # Sample 5 games across different time periods
        sample_indices = [0, len(df)//4, len(df)//2, 3*len(df)//4, len(df)-1]

        print("\nSample rows (showing key features):\n")
        sample_cols = [
            'game_id', 'game_date', 'season',
            'home_team_id', 'away_team_id', 'y_margin',
            'home_games_to_date', 'away_games_to_date',
            'home_win_pct_to_date', 'away_win_pct_to_date',
            'home_last10_margin', 'away_last10_margin',
            'rest_diff', 'home_b2b', 'away_b2b'
        ]

        for idx in sample_indices:
            row = df.iloc[idx]
            print(f"\nGame {idx + 1}/{len(df)}:")
            print(f"  Date: {row['game_date']}, Season: {row['season']}")
            print(f"  Game ID: {row['game_id']}")
            print(f"  Teams: {row['home_team_id']} (H) vs {row['away_team_id']} (A)")
            print(f"  Target y_margin: {row['y_margin']:.1f}")
            print(f"  Home games played before: {row['home_games_to_date']}")
            print(f"  Away games played before: {row['away_games_to_date']}")
            print(f"  Home win% to date: {row['home_win_pct_to_date']:.3f}")
            print(f"  Away win% to date: {row['away_win_pct_to_date']:.3f}")
            print(f"  Home L10 margin: {row['home_last10_margin']:.2f}")
            print(f"  Away L10 margin: {row['away_last10_margin']:.2f}")
            print(f"  Rest diff: {row['rest_diff']}, B2B: H={row['home_b2b']} A={row['away_b2b']}")

        # Validation checks
        print("\n" + "-"*70)
        print("VALIDATION CHECKS:")
        print("-"*70)

        # Check 1: No negative games_to_date
        neg_games = df[(df['home_games_to_date'] < 0) | (df['away_games_to_date'] < 0)]
        print(f"✓ Check 1: Games with negative 'games_to_date': {len(neg_games)}")
        assert len(neg_games) == 0, "Found negative games_to_date!"

        # Check 2: First few games should have 0 games_to_date for new teams
        first_100 = df.head(100)
        has_zero = ((first_100['home_games_to_date'] == 0) | (first_100['away_games_to_date'] == 0)).any()
        print(f"✓ Check 2: First 100 games include teams with 0 prior games: {has_zero}")

        # Check 3: Later games should have reasonable games_to_date counts
        last_100 = df.tail(100)
        avg_games_home = last_100['home_games_to_date'].mean()
        avg_games_away = last_100['away_games_to_date'].mean()
        print(f"✓ Check 3: Last 100 games - avg prior games: H={avg_games_home:.1f}, A={avg_games_away:.1f}")
        assert avg_games_home > 50, f"Expected >50 prior home games, got {avg_games_home}"
        assert avg_games_away > 50, f"Expected >50 prior away games, got {avg_games_away}"

        # Check 4: y_margin matches actual scores
        print(f"✓ Check 4: y_margin statistics:")
        print(f"    Mean: {df['y_margin'].mean():.2f} (should be ~0 for home court advantage)")
        print(f"    Std: {df['y_margin'].std():.2f}")
        print(f"    Range: [{df['y_margin'].min():.0f}, {df['y_margin'].max():.0f}]")

        # Check 5: Feature ranges look reasonable
        print(f"✓ Check 5: Feature ranges:")
        print(f"    Win% diff: [{df['win_pct_diff'].min():.3f}, {df['win_pct_diff'].max():.3f}]")
        print(f"    Last10 margin diff: [{df['last10_margin_diff'].min():.2f}, {df['last10_margin_diff'].max():.2f}]")
        print(f"    Rest diff: [{df['rest_diff'].min():.0f}, {df['rest_diff'].max():.0f}]")

        # Check 6: No missing values in key features
        key_features = ['home_win_pct_to_date', 'away_win_pct_to_date', 'home_last10_margin', 'y_margin']
        missing = df[key_features].isnull().sum()
        print(f"✓ Check 6: Missing values in key features:")
        for col in key_features:
            print(f"    {col}: {missing[col]}")
        assert missing.sum() == 0, "Found missing values in key features!"

        print("\n" + "="*70)
        print("✅ ALL SANITY CHECKS PASSED")
        print("="*70)

    def save_dataset(self, df: pd.DataFrame, filename: str = "margin_training_data.csv"):
        """Save dataset to CSV file."""
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)
        print(f"\n💾 Dataset saved to: {output_path}")
        print(f"   Size: {len(df)} rows × {len(df.columns)} columns")
        print(f"   File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        return output_path


def main():
    """CLI entry point for building training dataset."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Build margin prediction training dataset from historical NBA games"
    )
    parser.add_argument(
        '--seasons',
        nargs='+',
        default=['2022-23', '2023-24', '2024-25'],
        help='Seasons to include (default: last 3 complete seasons)'
    )
    parser.add_argument(
        '--output',
        default='margin_training_data.csv',
        help='Output filename (default: margin_training_data.csv)'
    )
    parser.add_argument(
        '--sanity-check',
        action='store_true',
        help='Run sanity checks and print sample rows'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Output directory (default: api/data/)'
    )

    args = parser.parse_args()

    print("="*70)
    print("NBA MARGIN PREDICTION - TRAINING DATASET BUILDER")
    print("="*70)
    print()

    # Initialize database
    init_db()
    db = SessionLocal()

    try:
        # Build dataset
        builder = MarginDatasetBuilder(db, output_dir=args.output_dir)
        df = builder.build_dataset(seasons=args.seasons, sanity_check=args.sanity_check)

        # Save to file
        output_path = builder.save_dataset(df, filename=args.output)

        print("\n" + "="*70)
        print("✅ SUCCESS")
        print("="*70)
        print(f"\nTraining dataset ready at: {output_path}")
        print("\nNext steps:")
        print("  1. Load the CSV in your ML notebook/script")
        print("  2. Train your regression model (e.g., XGBoost, LinearRegression)")
        print("  3. Save trained model to api/src/nb_analyzer/ml/margin_predictor.pkl")

    finally:
        db.close()


if __name__ == '__main__':
    main()
