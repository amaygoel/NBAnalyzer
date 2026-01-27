from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nba_predictor.database import init_db
from nba_predictor.routers import games_router, teams_router

app = FastAPI(
    title="NBA Predictor API",
    description="Betting insights and recommendations based on historical NBA data",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
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
