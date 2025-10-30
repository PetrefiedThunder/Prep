"""FastAPI application entrypoint."""

from fastapi import FastAPI

from prep.admin.api import router as admin_router
from prep.analytics.dashboard_api import router as analytics_router
from prep.api import admin_regulatory, auth, bookings, kitchens, regulatory, search
from prep.observability.metrics import MetricsMiddleware, create_metrics_router
from prep.api import admin_regulatory, auth, bookings, integrations, kitchens, regulatory, search
from prep.payments.api import router as payments_router
from prep.integrations.api import router as integrations_router
from prep.monitoring.api import router as monitoring_router
from prep.integrations.runtime import configure_integration_event_consumers

app = FastAPI(title="Prep Platform API", version="1.0.0")
app.add_middleware(MetricsMiddleware, app_name="prep-api")

app.include_router(create_metrics_router())
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
app.include_router(integrations_router)
app.include_router(monitoring_router)
configure_integration_event_consumers(app)

@app.get("/")
async def root() -> dict[str, str]:
    """Return API metadata."""

    return {"message": "Prep Platform API", "version": "1.0.0"}

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Provide a lightweight service health response."""

    return {"status": "healthy", "service": "prep-api"}
