from fastapi import FastAPI

from apps.api.routes import geometry, health, runs

app = FastAPI(
    title="Helios API",
    version="0.1.0",
    description="Explainable regional solar-site scouting, roof geometry, and ranking.",
)
app.include_router(health.router)
app.include_router(runs.router)
app.include_router(geometry.router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": "Helios",
        "status": "ready",
        "docs": "/docs",
        "health": "/health",
    }
