# NBAnalyzer - NBA Betting Insights Platform

AI-powered NBA betting recommendations based on historical data and real-time betting lines.

## Project Structure

```
NBAnalyzer/
├── api/              # FastAPI backend (Python)
│   ├── src/nb_analyzer/
│   │   ├── models/   # Database models (SQLAlchemy)
│   │   ├── routers/  # API endpoints
│   │   ├── services/ # Business logic
│   │   └── database.py
│   ├── scripts/      # Data ingestion scripts
│   ├── .env          # Environment variables (API keys)
│   └── pyproject.toml
└── web/              # Next.js frontend (TypeScript/React)
    ├── src/
    │   ├── app/      # Pages
    │   ├── components/
    │   └── lib/
    └── package.json
```

## Quick Start

### 1. Start Backend API
```bash
cd api
source venv/bin/activate
uvicorn nb_analyzer.main:app --reload
```
API runs at: **http://localhost:8000**

### 2. Start Frontend
```bash
cd web
npm run dev
```
Frontend runs at: **http://localhost:3000**

## Database

**Type:** SQLite (local file)
**Location:** `api/nb_analyzer.db`

### Tables
- `teams` - NBA teams (30 teams)
- `players` - Active NBA players (530 players)
- `games` - Game schedule (3,741 games across 3 seasons)
- `player_game_stats` - Box scores for each player/game
- `game_odds` - Betting lines (spread, total, moneyline)

### Current Data Status
- ✅ Teams: 30
- ✅ Players: 530 active
- ⏳ Player Stats: ~11,497 records (ingestion in progress)
- ✅ Games: 3,741 games (2022-23, 2023-24, 2024-25 seasons)
- ✅ Odds: 17 records (2 games with odds)

## Live Game Detection

### How It Works
- **Client-Side Detection:** Games automatically move to "Live" section when their scheduled start time passes
- **No Score Display:** Live games show "Live" badge only (no live scores - not real-time)
- **Frequent Updates:** API updates every 20 minutes during game hours (7 PM - 1 AM ET)
- **Quick Completion:** Games marked "Final" within 20-30 minutes of finishing

### Game States
1. **Upcoming:** Before start time - shows betting lines, clickable
2. **Live:** After start time, before completion - shows "Live" badge, not clickable
3. **Completed:** Marked final by NBA API - shows scores, not clickable

### Update Schedule
- **Game Hours (7 PM - 1 AM):** Every 20 minutes (19 updates)
- **Off Hours:** Every 6 hours (3 updates)
- **Total:** 22 game updates/day + 4 odds updates/day

## Data Ingestion

### Fetch Betting Odds
```bash
cd api
source venv/bin/activate
python scripts/fetch_odds.py
```
- Uses The Odds API
- Free tier: 500 requests/month
- Currently: 499 remaining

### Ingest Player Stats (Running in Background)
```bash
cd api
source venv/bin/activate
python scripts/ingest_player_stats.py
```
Status: Currently running (task ID: bc55499)

### Seed Full Database
```bash
cd api
source venv/bin/activate
python scripts/seed_database.py --seasons 2022-23 2023-24 2024-25
```

## API Endpoints

### Games
- `GET /api/games/week?days=7` - Get games for next 7 days with odds & recommendations
- `GET /api/games/today` - Today's games
- `GET /api/games/{game_id}` - Detailed game analysis
- `GET /api/games/date/{date}` - Games by specific date

### Teams
- `GET /api/teams/` - List all teams
- `GET /api/teams/{abbrev}/trends` - Team performance trends

## Environment Variables

### Backend (`api/.env`)
```bash
USE_SQLITE=true
ODDS_API_KEY=ba3afea908444320052430015db052d0
```

## Key Features

### Current Features ✅
1. **Conservative Value-Based Recommendations** - ONE focused bet per game (max)
   - Weighted analysis: 70% current season, 20% last season, 10% older
   - Only recommends when edge > 8%
   - Sanity checks: No extreme underdogs (+250), no near-.500 teams
   - Shows supporting stats and confidence level
2. **Betting Lines Display** - Spread, total, moneyline for each game
   - Automated updates 4x daily (8 AM, 2 PM, 5 PM, 10 PM ET)
   - Fetches odds for today + tomorrow
   - DraftKings odds (falls back to other books)
3. **Smart Weekly View** - Different display based on game timing
   - **Today**: Full odds + value-based recommendations
   - **Tomorrow**: Odds if available, "Lines coming soon" if not
   - **2+ days out**: Simple schedule view, odds available 1 day before game
4. **Game Detail Pages** - Comprehensive game analysis
   - Team records (W-L)
   - Betting lines breakdown
   - Team performance trends
   - Head-to-head history
   - Recent form (last 5 games)

### Planned Features 🎯
1. **Parlay of the Day** - Top 3 best bets combined
2. **Player Props Analysis** - Points, rebounds, assists over/under
3. **Betting Line Movement** - Track line changes over time
4. **Performance Tracking** - Historical record of recommendations
5. **Enhanced Detail Pages** - Better data visualization

## Recommendation Engine

### Current Logic (Conservative Value-Based) ✅
- **Focused Recommendations**: ONE best bet per game (max)
- **Weighted Season Analysis**:
  - Current season (2025-26): 70% weight
  - Last season (2024-25): 20% weight
  - Older season (2023-24): 10% weight
  - Emphasizes recent performance over historical data
- **Sanity Checks** (NEW):
  - Skip extreme underdogs (odds > +250)
  - Skip near-.500 teams with small samples (< 10 games)
  - Skip moneylines with < 50% win probability
  - Require minimum 5 current season games
- **Bet Options Evaluated**:
  - Home/Away Moneyline
  - Home/Away Spread (with 8% haircut for spread adjustment)
- **Value Betting**:
  - Compares weighted win % to implied probability from odds
  - Minimum 8% edge required
- **Confidence Levels**:
  - High: Edge > 12%
  - Medium: Edge 8-12%

### Example Output
```
HOU -10.5 (Home: 7-1 (this season))
Edge: +16.9%
Historical: 75% (weighted)
Implied: 52%
Odds: -108
Sample: 8 current season games
```

### Future Enhancements
- Total (over/under) recommendations with scoring analysis
- Player prop recommendations
- Line movement tracking

## Development Notes

### Tech Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy, nba_api
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS
- **Database:** SQLite (local), can switch to PostgreSQL
- **APIs:**
  - NBA Stats API (via nba_api package)
  - The Odds API (betting lines)

### Important Files
- `api/src/nb_analyzer/services/recommendations.py` - Recommendation logic
- `api/src/nb_analyzer/services/team_analysis.py` - Statistical analysis
- `web/src/components/GameCard.tsx` - Game display with odds
- `web/src/lib/api.ts` - TypeScript API types

### Common Commands

**Check player stats ingestion progress:**
```bash
cd api
source venv/bin/activate
python -c "from nb_analyzer.database import SessionLocal; from nb_analyzer.models import PlayerGameStats; db = SessionLocal(); print(f'Stats: {db.query(PlayerGameStats).count():,}'); db.close()"
```

**Fetch latest odds:**
```bash
cd api
source venv/bin/activate
python scripts/fetch_odds.py
```

**Check API status:**
```bash
curl http://localhost:8000/api/games/week?days=1 | python -m json.tool
```

## Odds Update Strategy

### Automated Schedule ✅
- **4 updates per day**: 8 AM, 2 PM, 5 PM, 10 PM ET
- **Coverage**: Today + tomorrow games
- **API Usage**: ~240 calls/month (well under 500 limit)

### Display Strategy
1. **Today**: Full betting lines + value-based recommendations
2. **Tomorrow**: Show odds when available (books post 24-48 hrs ahead)
3. **2+ days out**: Simple schedule view, no odds/recommendations yet

**Why This Works:**
- Betting lines change significantly 5-7 days out (injuries, news)
- Stale recommendations from a week ago are misleading
- Books typically post lines 24-48 hours before games
- Focuses user attention on actionable bets

### During Games
- Show "Live" badge
- Hide betting lines (not live betting)

### After Games
- Show final scores
- Historical data for future analysis

## Known Issues

### Fixed ✅
- ✅ Date timezone issues (rest days showing 287 days)
- ✅ NaN values in player stats ingestion
- ✅ Wrong season data (now using 2025-26)
- ✅ Broken recommendations (extreme underdogs with high confidence)
- ✅ Missing current season games (backfilled from Oct 22, 2025)

### Active
None - core functionality working as expected!

## API Rate Limits

### The Odds API
- **Free Tier:** 500 requests/month
- **Used:** 1 request
- **Remaining:** 499 requests
- **Strategy:** 2 updates/day = ~60/month (safe buffer)

### NBA Stats API
- No official limit
- Use 0.6s delay between requests to be respectful
- Rate limit handled in ingestion scripts

## Future Enhancements

### Phase 1: Value Betting (Next)
- Calculate implied probability from odds
- Compare to historical win rates
- Display edge % and expected value
- Conservative recommendations (>8% edge)

### Phase 2: Player Props
- Ingest player prop lines
- Analyze player trends
- Points, rebounds, assists projections
- Compare to over/under lines

### Phase 3: Polish
- Scheduled odds updates (cron)
- Bet tracking/slip feature
- Performance dashboard
- Mobile optimization

## Contributing

This is a personal project. Not open for contributions.

## License

Private project. All rights reserved.

## Contact

Project maintained by: Amay Goel
