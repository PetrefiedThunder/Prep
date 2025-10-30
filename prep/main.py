"""FastAPI application entrypoint."""

from fastapi import FastAPI

from prep.admin.api import router as admin_router
from prep.analytics.dashboard_api import router as analytics_router
from prep.api import admin_regulatory, auth, bookings, integrations, kitchens, regulatory, search
from prep.payments.api import router as payments_router

app = FastAPI(title="Prep Platform API", version="1.0.0")

app.include_router(auth.router)
app.include_router(kitchens.router)
app.include_router(bookings.router)
app.include_router(search.router)
app.include_router(regulatory.router)
app.include_router(admin_regulatory.router)
app.include_router(integrations.router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(analytics_router)

@app.get("/")
async def root() -> dict[str, str]:
    """Return API metadata."""

    return {"message": "Prep Platform API", "version": "1.0.0"}

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Provide a lightweight service health response."""

    return {"status": "healthy", "service": "prep-api"}
