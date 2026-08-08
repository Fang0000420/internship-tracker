from fastapi import FastAPI

from internship_tracker.api.routers.health import router as health_router
from internship_tracker.api.routers.internships import (
    router as internships_router,
)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Internship Tracker API",
        version="0.1.0",
        description="HTTP API for tracking European AI internship opportunities.",
    )
    application.include_router(health_router)
    application.include_router(internships_router)
    return application


app = create_app()
