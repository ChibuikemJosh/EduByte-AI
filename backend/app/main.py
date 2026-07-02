from fastapi import FastAPI

from app.database.database import init_db
from app.routes.health import router as health_router

app = FastAPI(title="EduByte AI Backend")


@app.get("/")
def root_health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.on_event("startup")
def startup_db() -> None:
    init_db()


app.include_router(health_router)