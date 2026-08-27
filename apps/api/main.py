from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import health, runs

app = FastAPI(
    title="Helios API",
    version="0.1.0",
    description="Explainable regional solar-site scouting and ranking.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router)
app.include_router(runs.router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": "Helios",
        "status": "ready",
        "docs": "/docs",
        "health": "/health",
    }
