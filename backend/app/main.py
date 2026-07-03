from fastapi import FastAPI

from app.database.database import init_db
from app.routes.ai import router as ai_router
from app.routes.auth import router as auth_router
from app.routes.chats import router as chats_router
from app.routes.courses import router as courses_router
from app.routes.health import router as health_router
from app.routes.modules import router as modules_router
from app.routes.progress import router as progress_router
from app.routes.quiz import router as quiz_router

app = FastAPI(title="EduByte AI Backend")


@app.get("/")
def root_health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.on_event("startup")
def startup_db() -> None:
    init_db()


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(chats_router)
app.include_router(courses_router)
app.include_router(modules_router)
app.include_router(progress_router)
app.include_router(quiz_router)
