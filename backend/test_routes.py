import os
import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

db_path = Path(tempfile.gettempdir()) / f"edubyte-test-{uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

import httpx

from app.database.database import init_db
from app.main import app
from app.schemas.schemas import CourseOutlinePayload, EduByteAIResponse, ModuleOutline, ResponseType
from app.services.ai_engine import AIEngineService


def _quiz_questions() -> list[dict]:
    return [
        {
            "question_id": index,
            "question_text": f"Question {index}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_option": "A",
        }
        for index in range(1, 11)
    ]


class RouteIntegrationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_db()
        cls.transport = httpx.ASGITransport(app=app)

    @classmethod
    def tearDownClass(cls) -> None:
        if db_path.exists():
            db_path.unlink()

    async def asyncSetUp(self) -> None:
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://testserver")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def _register_and_auth(self) -> dict[str, str]:
        suffix = uuid4().hex[:8]
        response = await self.client.post(
            "/auth/register",
            json={
                "username": f"user_{suffix}",
                "email": f"user_{suffix}@example.com",
                "password": "secret123",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def test_register_login_and_me(self) -> None:
        suffix = uuid4().hex[:8]
        register_response = await self.client.post(
            "/auth/register",
            json={
                "username": f"login_{suffix}",
                "email": f"login_{suffix}@example.com",
                "password": "secret123",
            },
        )
        self.assertEqual(register_response.status_code, 200, register_response.text)

        login_response = await self.client.post(
            "/auth/login",
            json={"login_identifier": f"login_{suffix}@example.com", "password": "secret123"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        me_response = await self.client.get("/auth/me", headers=headers)
        self.assertEqual(me_response.status_code, 200, me_response.text)
        self.assertEqual(me_response.json()["username"], f"login_{suffix}")

    async def test_chat_session_and_message_storage(self) -> None:
        headers = await self._register_and_auth()
        session_id = f"session-{uuid4().hex}"

        create_response = await self.client.post(
            "/chats",
            headers=headers,
            json={"session_id": session_id, "title": "Biology prep"},
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)

        message_response = await self.client.post(
            f"/chats/{session_id}/messages",
            headers=headers,
            json={"role": "user", "content": "Start a biology course"},
        )
        self.assertEqual(message_response.status_code, 201, message_response.text)

        detail_response = await self.client.get(f"/chats/{session_id}", headers=headers)
        self.assertEqual(detail_response.status_code, 200, detail_response.text)
        self.assertEqual(len(detail_response.json()["messages"]), 1)

    async def test_ai_generation_stores_session_messages_and_course(self) -> None:
        headers = await self._register_and_auth()
        session_id = f"ai-{uuid4().hex}"
        original_process_user_intent = AIEngineService.process_user_intent

        async def fake_process_user_intent(current_message, history_meta):
            return EduByteAIResponse(
                response_type=ResponseType.COURSE_OUTLINE,
                message="Course generated.",
                payload=CourseOutlinePayload(
                    response_type=ResponseType.COURSE_OUTLINE,
                    course_title="Intro Biology",
                    subject="Biology",
                    modules=[
                        ModuleOutline(
                            module_number=1,
                            module_title="Cell Basics",
                            subtopic_titles=["Cell theory", "Organelles"],
                        )
                    ],
                ),
            )

        AIEngineService.process_user_intent = fake_process_user_intent
        try:
            response = await self.client.post(
                "/ai/chat",
                headers=headers,
                json={"session_id": session_id, "message": "Create a biology course"},
            )
        finally:
            AIEngineService.process_user_intent = original_process_user_intent

        self.assertEqual(response.status_code, 200, response.text)

        chat_response = await self.client.get(f"/chats/{session_id}", headers=headers)
        self.assertEqual(chat_response.status_code, 200, chat_response.text)
        self.assertEqual(len(chat_response.json()["messages"]), 2)

        courses_response = await self.client.get("/courses", headers=headers)
        self.assertEqual(courses_response.status_code, 200, courses_response.text)
        self.assertEqual(courses_response.json()[0]["title"], "Intro Biology")

    async def test_progress_update_and_quiz_unlocks_next_module(self) -> None:
        headers = await self._register_and_auth()
        course_response = await self.client.post(
            "/courses",
            headers=headers,
            json={
                "course_title": "Python Backend",
                "subject": "Computer Science",
                "modules": [
                    {
                        "response_type": "MODULE_CONTENT",
                        "module_number": 1,
                        "module_title": "FastAPI Basics",
                        "subtopics": [{"title": "Routes", "content_markdown": "Routing content", "examples": []}],
                        "module_quiz": _quiz_questions(),
                    },
                    {
                        "module_number": 2,
                        "module_title": "Databases",
                        "subtopic_titles": ["SQL", "ORMs"],
                    },
                ],
            },
        )
        self.assertEqual(course_response.status_code, 201, course_response.text)
        modules = course_response.json()["modules"]
        first_module_id = modules[0]["id"]
        second_module_id = modules[1]["id"]

        progress_response = await self.client.post(
            "/progress",
            headers=headers,
            json={"module_id": first_module_id, "status": "IN_PROGRESS"},
        )
        self.assertEqual(progress_response.status_code, 200, progress_response.text)

        quiz_response = await self.client.post(
            "/quiz/submit",
            headers=headers,
            json={
                "module_id": first_module_id,
                "user_answers": {str(index): ("A" if index <= 7 else "B") for index in range(1, 11)},
            },
        )
        self.assertEqual(quiz_response.status_code, 200, quiz_response.text)
        quiz_data = quiz_response.json()
        self.assertTrue(quiz_data["passed"])
        self.assertEqual(quiz_data["score"], 70)
        self.assertEqual(quiz_data["unlocked_module_id"], second_module_id)

        next_progress = await self.client.get(f"/progress/{second_module_id}", headers=headers)
        self.assertEqual(next_progress.status_code, 200, next_progress.text)
        self.assertEqual(next_progress.json()["status"], "UNLOCKED")


if __name__ == "__main__":
    unittest.main()
