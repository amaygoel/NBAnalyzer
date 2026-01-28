# Deployment Guide

## Local Development

Uses SQLite by default. No configuration needed.

```bash
cd api
python -m venv venv
source venv/bin/activate  # or `./venv/bin/activate` on Windows
pip install -e .
uvicorn nb_analyzer.main:app --reload
```

## Production Deployment (Render)

### Database

Uses PostgreSQL. Render provides this automatically.

### Environment Variables

Set these in Render:
- `DATABASE_URL` - Automatically provided by Render when you add PostgreSQL
- `USE_SQLITE` - Set to `false` (or don't set it, defaults to false in production)
- `ODDS_API_KEY` - Your The Odds API key

### Migrations

Migrations run automatically on deploy. The database schema is created/updated automatically.

### Build Command
```bash
pip install -e .
```

### Start Command
```bash
# Run migrations first
alembic upgrade head

# Start the server
uvicorn nb_analyzer.main:app --host 0.0.0.0 --port $PORT
```

## Database Migrations

When you make schema changes:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations locally
alembic upgrade head

# Commit and push - migrations run automatically on Render
git add .
git commit -m "Add database migration"
git push
```
