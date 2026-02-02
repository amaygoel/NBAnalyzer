# NBAnalyzer

**AI-powered NBA betting insights platform using machine learning to identify value bets based on historical patterns and real-time odds.**

Built by [Amay Goel](https://github.com/amaygoel)

---

## Overview

NBAnalyzer is a full-stack web application that provides data-driven NBA betting recommendations. The platform uses a custom-trained XGBoost machine learning model to predict game outcomes, compares predictions against live betting markets, and surfaces high-value betting opportunities with confidence scoring.

### Key Features

- **ML-Powered Predictions**: XGBoost regression model trained on 4,375+ NBA games (3+ seasons) predicting point margins with 14.4 RMSE
- **Value Bet Detection**: Calculates Expected Value (EV) by comparing model predictions to market odds, highlighting positive-EV opportunities
- **Confidence Tiers**: Three-tier classification system (HIGH/MEDIUM/LOW) based on probability thresholds and expected value
- **Live Odds Integration**: Automated fetching from The Odds API with 4x daily updates
- **Automated Operations**: macOS LaunchAgent scheduler for data updates (games, odds, scores)
- **Responsive UI**: Clean, modern interface with team logos, live game tracking, and weekly schedule views

---

## Tech Stack

### Backend
- **Python 3.12** - Core language
- **FastAPI** - High-performance async API framework
- **SQLAlchemy** - ORM for database operations
- **XGBoost** - Gradient boosting ML model
- **Scikit-learn** - Model evaluation and metrics
- **NumPy/Pandas** - Data processing
- **NBA API** - Official NBA statistics
- **The Odds API** - Real-time betting lines

### Frontend
- **Next.js 15** (App Router) - React framework with SSR
- **React 19** - UI library
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first styling
- **Lucide Icons** - Icon library

### Database & Infrastructure
- **SQLite** - Local development database
- **Git** - Version control
- **macOS LaunchAgents** - Task automation

---

## Architecture

```
NBAnalyzer/
├── api/                          # Python FastAPI backend
│   ├── src/nb_analyzer/
│   │   ├── ml/                   # Machine learning module
│   │   │   ├── model_trainer.py  # XGBoost training pipeline
│   │   │   ├── inference.py      # Prediction engine
│   │   │   └── bet_selector.py   # EV calculation & bet selection
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── routers/              # API endpoints
│   │   ├── services/             # Business logic
│   │   └── database.py           # DB connection
│   ├── scripts/                  # Data ingestion scripts
│   │   ├── run_ops.py           # Production orchestrator
│   │   ├── fetch_odds.py        # Betting lines fetcher
│   │   ├── fetch_upcoming_games.py
│   │   └── fetch_todays_games.py
│   └── nb_analyzer.db           # SQLite database
│
└── web/                          # Next.js frontend
    ├── src/
    │   ├── app/                  # App Router pages
    │   │   ├── page.tsx         # Home page
    │   │   └── game/[id]/       # Game detail pages
    │   ├── components/           # React components
    │   │   ├── GameCard.tsx     # Game display with ML pick
    │   │   └── WeeklyGamesTabs.tsx
    │   └── lib/
    │       └── api.ts           # TypeScript API client
    └── public/                   # Static assets
```

---

## Machine Learning Pipeline

### 1. Data Collection
- Historical game data from NBA API (2022-2026)
- 4,375 completed games with final margins
- Team performance metrics, win/loss records, standings

### 2. Feature Engineering
- Home/away team records (wins, losses, win percentage)
- Team standings and rankings
- Binary home court advantage indicator

### 3. Model Training
- **Algorithm**: XGBoost Regressor
- **Target**: Point margin (home team perspective)
- **Validation**: 80/20 train-test split
- **Performance**: 14.4 RMSE, 0.21 R²
- **Output**: Predicted margin → converted to probabilities via normal distribution

### 4. Bet Selection
- Convert predicted margins to win/cover probabilities
- Calculate implied probability from American odds
- Compute Expected Value: `EV = (model_prob × payout) - 1`
- Filter bets meeting minimum EV thresholds (3-6%)
- Classify confidence: HIGH (6%+ EV), MEDIUM (3-6%), LOW (0-3%)

---

## API Endpoints

### Games
```
GET  /api/games/today               # Today's games with odds & recommendations
GET  /api/games/week?days=7         # Next 7 days of games
GET  /api/games/{game_id}           # Detailed game analysis
GET  /api/games/date/{YYYY-MM-DD}   # Games by specific date
```

### Teams
```
GET  /api/teams/                    # All NBA teams
GET  /api/teams/{abbrev}            # Team details
```

---

## Automated Operations

Production automation runs via **macOS LaunchAgents**:

- **Daily Updates (5 AM)**: Fetch upcoming games schedule (14 days out)
- **Odds Refresh (4x daily)**: Update betting lines at 8 AM, 2 PM, 5 PM, 10 PM
- **Score Updates (every 20 min)**: Update game results during prime hours (6 PM - 1 AM)

See `api/LAUNCHD.md` and `api/OPS.md` for details.

---

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 18+
- NBA API access
- The Odds API key (free tier: 500 requests/month)

### Backend Setup
```bash
cd api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
cp .env.example .env      # Add your ODDS_API_KEY

# Initialize database and train model
python scripts/seed_database.py
python scripts/train_margin_model.py

# Start API server
uvicorn nb_analyzer.main:app --reload
# API available at http://localhost:8000
```

### Frontend Setup
```bash
cd web
npm install
npm run dev
# UI available at http://localhost:3000
```

---

## Database Schema

**Core Tables:**
- `teams` - 30 NBA teams with metadata
- `games` - Game schedule, scores, completion status
- `game_odds` - Spread, total, moneyline from multiple sportsbooks
- `players` - Active NBA players
- `player_game_stats` - Box scores and performance data

---

## Project Highlights

### Technical Achievements
- Built end-to-end ML pipeline from data collection to production inference
- Designed RESTful API with proper separation of concerns (routers, services, models)
- Implemented Expected Value betting framework with confidence classification
- Created responsive React UI with server-side rendering for optimal performance
- Automated data pipeline with cron-like scheduling on macOS

### Engineering Decisions
- **XGBoost over Neural Networks**: Faster training, better interpretability, sufficient for tabular data
- **SQLite for MVP**: Simple deployment, easy backups, sufficient for single-user application
- **Probability Calibration**: Used normal distribution with empirical RMSE as sigma for converting point predictions to probabilities
- **Conservative Betting Thresholds**: Required 3%+ EV to account for model uncertainty and betting overhead

---

## Future Enhancements

- [ ] Player prop predictions (points, rebounds, assists)
- [ ] Line movement tracking and alerting
- [ ] Historical recommendation performance dashboard
- [ ] PostgreSQL migration for production deployment
- [ ] Mobile app (React Native)
- [ ] Parlay optimizer

---

## License

Private project. All rights reserved.

---

## Contact

**Amay Goel**
[LinkedIn](https://linkedin.com/in/amaygoel) • [GitHub](https://github.com/amaygoel)

*Disclaimer: This project is for educational and entertainment purposes only. Not financial advice.*
