from fastapi import FastAPI

from app.middleware.error_handlers import register_error_handlers
from app.routers import preferences

app = FastAPI(
    title="Notification Preferences API",
    description="Multi-tenant notification preferences management",
    version="1.0.0",
)

register_error_handlers(app)
app.include_router(preferences.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
