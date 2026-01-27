# NBA Predictor API

Backend service for NBA betting insights and recommendations.

## Setup

1. Create a virtual environment:
```bash
cd api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e .
```

3. Seed the database (this takes a while - fetches 3 seasons of data):
```bash
python scripts/seed_database.py
```

To seed specific seasons:
```bash
python scripts/seed_database.py --seasons 2023-24 2024-25
```

4. Run the API server:
```bash
uvicorn nb_analyzer.main:app --reload
```

API will be available at http://localhost:8000

## Project Structure

```
api/
├── src/nb_analyzer/
│   ├── models/          # SQLAlchemy database models
│   ├── routers/         # API route handlers
│   ├── services/        # Business logic
│   ├── config.py        # Configuration
│   ├── database.py      # Database setup
│   └── main.py          # FastAPI app
├── scripts/             # Data ingestion scripts
└── pyproject.toml       # Dependencies
```
