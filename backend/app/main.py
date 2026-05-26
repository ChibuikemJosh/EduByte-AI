from fastapi import FastAPI

from app.routes.health import router as health_router

app = FastAPI(title="EduByte AI Backend")


@app.get("/")
def root_health_check() -> dict[str, str]:
    return {"status": "healthy"}


app.include_router(health_router)