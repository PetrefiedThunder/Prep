"""FastAPI application entrypoint."""

from fastapi import FastAPI

from prep.api import auth, kitchens

app = FastAPI(title="Prep Platform API", version="1.0.0")

app.include_router(auth.router)
app.include_router(kitchens.router)

@app.get("/")
async def root() -> dict[str, str]:
    """Return API metadata."""

    return {"message": "Prep Platform API", "version": "1.0.0"}

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Provide a lightweight service health response."""

    return {"status": "healthy", "service": "prep-api"}
