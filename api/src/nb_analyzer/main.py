from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nb_analyzer.database import init_db
from nb_analyzer.routers import games_router, teams_router

app = FastAPI(
    title="NBA Predictor API",
    description="Betting insights and recommendations based on historical NBA data",
    version="0.1.0",
)

# CORS for frontend - Allow all origins for now (restrict to your domain later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins is ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(games_router, prefix="/api")
app.include_router(teams_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "NBA Predictor API", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/admin/seed-database")
def seed_database_endpoint():
    """
    One-time endpoint to seed the production database.
    Call this once after deployment to populate teams and games.
    """
    import subprocess
    import sys
    from pathlib import Path

    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "seed_production.py"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Seeding timed out after 5 minutes"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/admin/fetch-odds")
def fetch_odds_endpoint():
    """Manually trigger odds fetching."""
    import subprocess
    import sys
    from pathlib import Path

    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "fetch_odds.py"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
