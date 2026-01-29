#!/usr/bin/env python3
"""
Train margin prediction model (Ridge regression with standardized features).

Splits by season for proper evaluation:
- Train: 2022-23 + 2023-24
- Val: 2024-25
- Test: 2025-26 (if present)

Saves trained pipeline + metadata to artifacts/
"""
import sys
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Feature columns used for training
FEATURE_COLS = [
    'home_win_pct_to_date',
    'away_win_pct_to_date',
    'win_pct_diff',
    'home_last10_margin',
    'away_last10_margin',
    'last10_margin_diff',
    'home_home_margin_to_date',
    'away_away_margin_to_date',
    'rest_diff',
    'home_b2b',
    'away_b2b',
]

TARGET_COL = 'y_margin'


def load_and_split_data(data_path: Path):
    """
    Load dataset and split by season.

    Returns:
        dict with keys: 'train', 'val', 'test' (each contains X, y, df)
    """
    print(f"Loading data from: {data_path}")
    df = pd.read_csv(data_path)

    print(f"Dataset: {len(df)} games")
    print(f"Date range: {df['game_date'].min()} to {df['game_date'].max()}")

    # Check available seasons
    seasons_available = sorted(df['season'].unique())
    print(f"Seasons available: {seasons_available}")

    # Split by season
    splits = {}

    # Train: 2022-23 + 2023-24
    train_seasons = ['2022-23', '2023-24']
    train_mask = df['season'].isin(train_seasons)
    train_df = df[train_mask]
    if len(train_df) > 0:
        splits['train'] = {
            'df': train_df,
            'X': train_df[FEATURE_COLS],
            'y': train_df[TARGET_COL],
            'seasons': train_seasons
        }
        print(f"Train: {len(train_df)} games from {train_seasons}")
    else:
        print(f"⚠️  No data found for train seasons {train_seasons}")
        splits['train'] = None

    # Val: 2024-25
    val_season = '2024-25'
    val_mask = df['season'] == val_season
    val_df = df[val_mask]
    if len(val_df) > 0:
        splits['val'] = {
            'df': val_df,
            'X': val_df[FEATURE_COLS],
            'y': val_df[TARGET_COL],
            'seasons': [val_season]
        }
        print(f"Val: {len(val_df)} games from {val_season}")
    else:
        print(f"⚠️  No data found for val season {val_season}")
        splits['val'] = None

    # Test: 2025-26
    test_season = '2025-26'
    test_mask = df['season'] == test_season
    test_df = df[test_mask]
    if len(test_df) > 0:
        splits['test'] = {
            'df': test_df,
            'X': test_df[FEATURE_COLS],
            'y': test_df[TARGET_COL],
            'seasons': [test_season]
        }
        print(f"Test: {len(test_df)} games from {test_season}")
    else:
        print(f"⚠️  No data found for test season {test_season} (this is OK if season incomplete)")
        splits['test'] = None

    return splits


def evaluate_model(pipeline, X, y, split_name: str):
    """Evaluate model and return metrics dict."""
    y_pred = pipeline.predict(X)

    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))

    # Winner direction accuracy (does predicted margin sign match actual?)
    correct_direction = ((y_pred > 0) == (y > 0)).sum()
    direction_acc = correct_direction / len(y)

    metrics = {
        'mae': float(mae),
        'rmse': float(rmse),
        'direction_accuracy': float(direction_acc),
        'n_samples': len(y)
    }

    print(f"\n{split_name} Metrics ({len(y)} games):")
    print(f"  MAE:  {mae:.2f} points")
    print(f"  RMSE: {rmse:.2f} points")
    print(f"  Winner Direction Accuracy: {direction_acc:.1%} ({correct_direction}/{len(y)})")

    return metrics


def train_model(splits, alphas=[0.1, 1.0, 10.0, 50.0, 100.0]):
    """
    Train Ridge regression with grid search over alpha on validation set.

    Returns:
        best_pipeline, best_alpha, all_metrics
    """
    if splits['train'] is None:
        raise ValueError("No training data available")

    X_train = splits['train']['X']
    y_train = splits['train']['y']

    print("\n" + "="*70)
    print("TRAINING MARGIN PREDICTION MODEL")
    print("="*70)

    print(f"\nGrid search over alpha: {alphas}")

    # Use validation set for alpha selection if available, else use train
    if splits['val'] is not None:
        X_val = splits['val']['X']
        y_val = splits['val']['y']
        print("Using validation set for alpha selection")
    else:
        print("⚠️  No validation set - using training set for alpha selection")
        X_val = X_train
        y_val = y_train

    best_alpha = None
    best_val_mae = float('inf')
    best_pipeline = None

    for alpha in alphas:
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('ridge', Ridge(alpha=alpha, random_state=42))
        ])

        pipeline.fit(X_train, y_train)
        y_val_pred = pipeline.predict(X_val)
        val_mae = mean_absolute_error(y_val, y_val_pred)

        print(f"  α={alpha:>6.1f} → Val MAE: {val_mae:.3f}")

        if val_mae < best_val_mae:
            best_val_mae = val_mae
            best_alpha = alpha
            best_pipeline = pipeline

    print(f"\n✅ Best alpha: {best_alpha} (Val MAE: {best_val_mae:.3f})")

    # Evaluate on all splits
    all_metrics = {}

    print("\n" + "="*70)
    print("FINAL MODEL EVALUATION")
    print("="*70)

    if splits['train'] is not None:
        all_metrics['train'] = evaluate_model(
            best_pipeline, splits['train']['X'], splits['train']['y'], 'Train'
        )

    if splits['val'] is not None:
        all_metrics['val'] = evaluate_model(
            best_pipeline, splits['val']['X'], splits['val']['y'], 'Validation'
        )

    if splits['test'] is not None:
        all_metrics['test'] = evaluate_model(
            best_pipeline, splits['test']['X'], splits['test']['y'], 'Test'
        )

    return best_pipeline, best_alpha, all_metrics


def print_coefficients(pipeline, feature_cols):
    """Print feature coefficients if model is linear."""
    print("\n" + "="*70)
    print("FEATURE COEFFICIENTS (Standardized)")
    print("="*70)

    ridge_model = pipeline.named_steps['ridge']
    coefs = ridge_model.coef_

    # Sort by absolute value
    coef_df = pd.DataFrame({
        'feature': feature_cols,
        'coefficient': coefs,
        'abs_coef': np.abs(coefs)
    }).sort_values('abs_coef', ascending=False)

    print("\nFeatures ranked by importance (absolute coefficient):\n")
    for idx, row in coef_df.iterrows():
        sign = '+' if row['coefficient'] > 0 else ''
        print(f"  {row['feature']:30s}  {sign}{row['coefficient']:>8.4f}")

    print(f"\nIntercept: {ridge_model.intercept_:.4f}")


def save_artifacts(pipeline, best_alpha, all_metrics, splits, output_dir: Path):
    """Save trained model + metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = output_dir / "margin_model.pkl"
    joblib.dump(pipeline, model_path)
    print(f"\n💾 Model saved to: {model_path}")

    # Collect metadata
    metadata = {
        'trained_at': datetime.now().isoformat(),
        'feature_columns': FEATURE_COLS,
        'target_column': TARGET_COL,
        'model_type': 'Ridge',
        'best_alpha': best_alpha,
        'metrics': all_metrics,
        'train_seasons': splits['train']['seasons'] if splits['train'] else [],
        'val_seasons': splits['val']['seasons'] if splits['val'] else [],
        'test_seasons': splits['test']['seasons'] if splits['test'] else [],
        'n_features': len(FEATURE_COLS),
    }

    # Save metadata
    metadata_path = output_dir / "margin_model_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"📄 Metadata saved to: {metadata_path}")

    # Print summary
    print("\n" + "="*70)
    print("✅ MODEL TRAINING COMPLETE")
    print("="*70)
    print(f"\nModel artifacts:")
    print(f"  Model:    {model_path}")
    print(f"  Metadata: {metadata_path}")
    print(f"\nBest hyperparameter: α = {best_alpha}")
    print(f"\nPerformance summary:")
    for split, metrics in all_metrics.items():
        print(f"  {split.capitalize():12s}  MAE: {metrics['mae']:.2f}  RMSE: {metrics['rmse']:.2f}  Accuracy: {metrics['direction_accuracy']:.1%}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Train margin prediction model"
    )
    parser.add_argument(
        '--data',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'margin_training_data.csv',
        help='Path to training data CSV'
    )
    parser.add_argument(
        '--outdir',
        type=Path,
        default=Path(__file__).parent.parent / 'src' / 'nb_analyzer' / 'ml' / 'artifacts',
        help='Output directory for model artifacts'
    )
    parser.add_argument(
        '--rebuild-data',
        action='store_true',
        help='Rebuild training dataset before training'
    )
    parser.add_argument(
        '--print-coefs',
        action='store_true',
        help='Print feature coefficients (weights)'
    )
    parser.add_argument(
        '--alphas',
        nargs='+',
        type=float,
        default=[0.1, 1.0, 10.0, 50.0, 100.0],
        help='Alpha values for grid search'
    )

    args = parser.parse_args()

    print("="*70)
    print("NBA MARGIN PREDICTION MODEL - TRAINING PIPELINE")
    print("="*70)
    print()

    # Rebuild data if requested
    if args.rebuild_data:
        print("Rebuilding training dataset...")
        from nb_analyzer.ml.dataset_builder import MarginDatasetBuilder
        from nb_analyzer.database import SessionLocal, init_db

        init_db()
        db = SessionLocal()
        try:
            builder = MarginDatasetBuilder(db)
            df = builder.build_dataset(seasons=['2022-23', '2023-24', '2024-25', '2025-26'])
            data_path = builder.output_dir / 'margin_training_data.csv'
            builder.save_dataset(df, filename='margin_training_data.csv')
            args.data = data_path
        finally:
            db.close()
        print()

    # Check data file exists
    if not args.data.exists():
        print(f"❌ Error: Data file not found: {args.data}")
        print("\nPlease run dataset builder first:")
        print("  ./venv/bin/python scripts/build_training_dataset.py")
        print("\nOr use --rebuild-data flag to rebuild automatically")
        sys.exit(1)

    # Load and split data
    splits = load_and_split_data(args.data)

    # Train model
    try:
        pipeline, best_alpha, all_metrics = train_model(splits, alphas=args.alphas)
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    # Print coefficients if requested
    if args.print_coefs:
        print_coefficients(pipeline, FEATURE_COLS)

    # Save artifacts
    save_artifacts(pipeline, best_alpha, all_metrics, splits, args.outdir)

    print("\n" + "="*70)
    print("Next steps:")
    print("  1. Review model metrics above")
    print("  2. If satisfied, integrate into recommendations.py")
    print("  3. Test predictions on upcoming games")
    print("="*70)


if __name__ == '__main__':
    main()
