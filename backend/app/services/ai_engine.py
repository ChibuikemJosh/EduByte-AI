import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from groq import Groq, RateLimitError

from app.schemas.schemas import (
    CourseOutlinePayload,
    EduByteAIResponse,
    FollowUpPayload,
    ModuleOutline,
    ResponseType,
)

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

MASTER_ROUTER_PROMPT = """
You are EduByte AI's router. Return exactly one JSON object.

Rules:
- COURSE_OUTLINE: produce at least 5 modules.
- PRACTICE_QUIZ: produce exactly 10 questions.
- GENERAL_QUESTION_ANSWER: answer directly.
- FOLLOW_UP: ask only if critical details are missing.
- Keep quiz answers balanced; no option letter should appear more than 3 times.
""".strip()

SUBTOPIC_CONTENT_PROMPT = """
Write JSON-safe Markdown content for one subtopic.

Requirements:
- Return title, content_markdown, and examples.
- Do not use triple quotes, raw code fences, or unescaped backticks.
""".strip()

QUIZ_GENERATION_PROMPT = """
Generate a JSON object for a 10-question multiple-choice quiz.

Requirements:
- Exactly 10 questions.
- Plain text options only.
- correct_option must be A, B, C, or D.
- No answer letter should appear more than 3 times.
- Keep all strings JSON-safe.
""".strip()


class AIEngineService:
    @staticmethod
    def format_history_context(history_meta: List[Dict[str, Any]], current_message: str) -> str:
        context_block = "CONVERSATION HISTORY RECORDS:\n"
        for turn in history_meta:
            role = "User" if turn.get("role") == "user" else "EduByteAI"
            content = turn.get("content", "")
            context_block += f"[{role}]: {content}\n"
        context_block += f"\nNEW CLIENT CURRENT UTTERANCE: '{current_message}'\n"
        return context_block

    @staticmethod
    def _normalize_response_content(raw_content: Any) -> Any:
        if isinstance(raw_content, dict):
            return raw_content
        if raw_content is None:
            return {}
        if isinstance(raw_content, str) and raw_content.strip() == "":
            return {}
        try:
            return json.loads(raw_content)
        except (json.JSONDecodeError, TypeError) as exc:
            logging.warning("Groq response was not valid JSON: %s", exc)
            return {}

    @staticmethod
    def _build_rate_limit_fallback_response(current_message: str) -> EduByteAIResponse:
        lowered_message = current_message.lower()
        if any(keyword in lowered_message for keyword in ["learn", "study", "course", "roadmap", "syllabus", "outline"]):
            modules = [
                ModuleOutline(module_number=1, module_title="Python Foundations", subtopic_titles=["Variables and Data Types", "Control Flow", "Functions and Modules"]),
                ModuleOutline(module_number=2, module_title="Web Basics", subtopic_titles=["HTTP Concepts", "Client-Server Flow", "Request and Response Lifecycle"]),
                ModuleOutline(module_number=3, module_title="Backend Frameworks", subtopic_titles=["Flask Basics", "Routing and Views", "Templates and Forms"]),
                ModuleOutline(module_number=4, module_title="Data and APIs", subtopic_titles=["Database Fundamentals", "CRUD APIs", "JSON Serialization"]),
                ModuleOutline(module_number=5, module_title="Deployment and Testing", subtopic_titles=["Environment Variables", "Testing Strategies", "Deployment Basics"]),
            ]
            return EduByteAIResponse(
                response_type=ResponseType.COURSE_OUTLINE,
                message="I drafted a local course outline because the model hit its request limit.",
                payload=CourseOutlinePayload(
                    response_type=ResponseType.COURSE_OUTLINE,
                    course_title="Introductory Backend Web Development with Python",
                    subject="Backend Development",
                    modules=modules,  # type: ignore[arg-type]
                ),
            )

        return EduByteAIResponse(
            response_type=ResponseType.FOLLOW_UP,
            message="I hit a temporary model request limit.",
            payload=FollowUpPayload(
                response_type=ResponseType.FOLLOW_UP,
                clarification_text="Please try again in a few minutes, or send a shorter request so I can answer locally.",
            ),
        )

    @staticmethod
    def _normalize_outline_payload(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload

        normalized = dict(payload)
        if "title" in normalized and "course_title" not in normalized:
            normalized["course_title"] = normalized.pop("title")

        modules = normalized.get("modules")
        if isinstance(modules, list):
            normalized_modules = []
            for module in modules:
                if not isinstance(module, dict):
                    normalized_modules.append(module)
                    continue

                normalized_module = dict(module)
                if "module_id" in normalized_module and "module_number" not in normalized_module:
                    normalized_module["module_number"] = normalized_module.pop("module_id")
                if "module_name" in normalized_module and "module_title" not in normalized_module:
                    normalized_module["module_title"] = normalized_module.pop("module_name")
                if "subtopics" in normalized_module and "subtopic_titles" not in normalized_module:
                    subtopics = normalized_module.pop("subtopics")
                    if isinstance(subtopics, list):
                        normalized_module["subtopic_titles"] = [
                            item.get("title") if isinstance(item, dict) else item for item in subtopics
                        ]
                if "subtopic_list" in normalized_module and "subtopic_titles" not in normalized_module:
                    subtopics = normalized_module.pop("subtopic_list")
                    if isinstance(subtopics, list):
                        normalized_module["subtopic_titles"] = [
                            item.get("title") if isinstance(item, dict) else item for item in subtopics
                        ]

                normalized_modules.append(normalized_module)

            normalized["modules"] = normalized_modules

        return normalized

    @classmethod
    async def generate_subtopic_text_block(cls, module_title: str, all_subtopics: List[str], target_subtopic: str) -> Dict[str, Any]:
        if not client:
            raise RuntimeError("Groq Client uninitialized.")

        input_payload = {
            "parent_module_title": module_title,
            "sibling_context_subtopics": all_subtopics,
            "target_subtopic_to_explain": target_subtopic,
        }

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SUBTOPIC_CONTENT_PROMPT},
                {"role": "user", "content": json.dumps(input_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.25,
            max_tokens=2000,
        )
        return cls._normalize_response_content(response.choices[0].message.content or "{}")

    @classmethod
    async def generate_isolated_quiz_block(cls, module_title: str, subtopic_titles: List[str], history_meta: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not client:
            raise RuntimeError("Groq Client uninitialized.")

        input_payload = {
            "module_title": module_title,
            "subtopics_covered": subtopic_titles,
            "historical_chat_context": history_meta,
        }

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": QUIZ_GENERATION_PROMPT},
                {"role": "user", "content": json.dumps(input_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.20,
            max_tokens=4000,
        )

        raw_data = cls._normalize_response_content(response.choices[0].message.content or "{}")
        if not isinstance(raw_data, dict):
            return []

        payload = raw_data.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("questions"), list):
            return payload["questions"]

        questions = raw_data.get("questions")
        if isinstance(questions, list):
            return questions

        return []

    @classmethod
    async def process_user_intent(cls, current_message: str, history_meta: List[Dict[str, Any]]) -> EduByteAIResponse:
        compiled_contents = cls.format_history_context(history_meta, current_message)

        response = None
        if client:
            try:
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": MASTER_ROUTER_PROMPT},
                        {"role": "user", "content": compiled_contents},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.10,
                )
            except RateLimitError:
                logging.warning("Groq rate limit reached; using local fallback response.")
                return cls._build_rate_limit_fallback_response(current_message)

        raw_content = None
        if response and getattr(response, "choices", None):
            try:
                raw_content = response.choices[0].message.content
            except Exception:
                raw_content = None

        parsed_content = cls._normalize_response_content(raw_content)
        if isinstance(parsed_content, dict) and ("message" not in parsed_content or "payload" not in parsed_content):
            alias_map = {
                "course_outline": ResponseType.COURSE_OUTLINE,
                "practice_quiz": ResponseType.PRACTICE_QUIZ,
                "general_question_answer": ResponseType.GENERAL_QUESTION_ANSWER,
                "follow_up": ResponseType.FOLLOW_UP,
            }
            for alias_key, response_type in alias_map.items():
                alias_payload = parsed_content.get(alias_key)
                if isinstance(alias_payload, dict):
                    parsed_content = {
                        "response_type": response_type.value,
                        "message": alias_payload.get("message") or parsed_content.get("message") or "",
                        "payload": cls._normalize_outline_payload(alias_payload.get("payload") or {k: v for k, v in alias_payload.items() if k != "message"}),
                    }
                    break

        if isinstance(parsed_content, dict) and not parsed_content.get("message"):
            parsed_content["message"] = ""

        if isinstance(parsed_content, dict) and "payload" not in parsed_content:
            parsed_content["payload"] = {}

        if not parsed_content.get("response_type"):
            parsed_content["response_type"] = ResponseType.FOLLOW_UP.value

        if parsed_content.get("response_type") == ResponseType.COURSE_OUTLINE.value:
            payload_data = parsed_content.get("payload", {})
            modules_list = payload_data.get("modules", [])
            if modules_list:
                mod_one = modules_list[0]
                m_title = mod_one.get("module_title")
                subs = mod_one.get("subtopic_titles", [])
                print(f"⚡️ [Orchestrator] Firing {len(subs)} Text and 1 Quiz generation tasks parallelly...")

                text_tasks = [cls.generate_subtopic_text_block(m_title, subs, s) for s in subs]
                quiz_task = cls.generate_isolated_quiz_block(m_title, subs, history_meta)
                gathered_results = await asyncio.gather(*text_tasks, quiz_task, return_exceptions=True)

                if not any(isinstance(result, Exception) for result in gathered_results):
                    completed_quiz = gathered_results[-1]
                    if isinstance(completed_quiz, list):
                        parsed_content["payload"]["modules"][0] = {
                            "response_type": ResponseType.MODULE_CONTENT.value,
                            "module_number": mod_one.get("module_number", 1),
                            "module_title": m_title,
                            "subtopics": gathered_results[:-1],
                            "module_quiz": completed_quiz,
                        }

        if isinstance(parsed_content.get("payload"), dict):
            parsed_content["payload"].setdefault("response_type", parsed_content.get("response_type"))

        def _validate_quiz_questions(questions: list[dict]) -> Tuple[bool, str]:
            if not isinstance(questions, list):
                return False, "questions must be a list"
            if len(questions) != 10:
                return False, "quiz must contain exactly 10 questions"
            counts = {"A": 0, "B": 0, "C": 0, "D": 0}
            for question in questions:
                opt = question.get("correct_option")
                if opt in counts:
                    counts[opt] += 1
            if any(value > 4 for value in counts.values()):
                return False, "correct options distribution is unbalanced"
            return True, ""

        def _scan_and_validate(obj: Any) -> Tuple[bool, str]:
            if isinstance(obj, dict):
                questions = obj.get("questions")
                if isinstance(questions, list):
                    return _validate_quiz_questions(questions)
                module_quiz = obj.get("module_quiz")
                if isinstance(module_quiz, list):
                    return _validate_quiz_questions(module_quiz)
                modules = obj.get("modules")
                if isinstance(modules, list):
                    for module in modules:
                        ok, reason = _scan_and_validate(module)
                        if not ok:
                            return ok, reason
            elif isinstance(obj, list):
                for item in obj:
                    ok, reason = _scan_and_validate(item)
                    if not ok:
                        return ok, reason
            return True, ""

        ok, reason = _scan_and_validate(parsed_content.get("payload"))
        if not ok:
            def _find_quiz_location(obj: Any) -> Tuple[str, dict, str, list] | None:
                if isinstance(obj, dict):
                    if obj.get("questions") is not None:
                        return ("practice", obj, obj.get("quiz_title", "General"), [])
                    if obj.get("module_quiz") is not None:
                        subtopics = []
                        raw_subtopics = obj.get("subtopics") or obj.get("subtopic_titles")
                        if isinstance(raw_subtopics, list):
                            for subtopic in raw_subtopics:
                                if isinstance(subtopic, dict):
                                    subtopics.append(subtopic.get("title"))
                                else:
                                    subtopics.append(subtopic)
                        return ("module", obj, obj.get("module_title") or obj.get("title", "Module"), subtopics)
                    modules = obj.get("modules")
                    if isinstance(modules, list):
                        for module in modules:
                            found = _find_quiz_location(module)
                            if found:
                                return found
                elif isinstance(obj, list):
                    for item in obj:
                        found = _find_quiz_location(item)
                        if found:
                            return found
                return None

            def _rebalance_questions(questions: list[dict]) -> list[dict]:
                counts = {"A": 0, "B": 0, "C": 0, "D": 0}
                for question in questions:
                    opt = question.get("correct_option")
                    if opt in counts:
                        counts[opt] += 1

                attempts = 0
                while any(value > 4 for value in counts.values()):
                    over = max(counts, key=lambda key: counts[key])
                    under = min(counts, key=lambda key: counts[key])
                    for question in questions:
                        if question.get("correct_option") == over:
                            question["correct_option"] = under
                            counts[over] -= 1
                            counts[under] += 1
                            break
                    attempts += 1
                    if attempts > 20:
                        break
                return questions

            location = _find_quiz_location(parsed_content.get("payload"))
            regenerated = False
            if location:
                kind, parent, module_title, subtopics = location
                for _ in range(2):
                    try:
                        new_questions = await cls.generate_isolated_quiz_block(module_title or "General", subtopics or [], history_meta)
                    except Exception:
                        new_questions = None
                    if new_questions:
                        valid, _ = _validate_quiz_questions(new_questions)
                        if valid:
                            if kind == "practice":
                                parent["questions"] = new_questions
                            else:
                                parent["module_quiz"] = new_questions
                            regenerated = True
                            break

                if not regenerated:
                    existing_questions = parent.get("questions") or parent.get("module_quiz")
                    if isinstance(existing_questions, list):
                        balanced = _rebalance_questions(existing_questions)
                        valid, _ = _validate_quiz_questions(balanced)
                        if valid:
                            if kind == "practice":
                                parent["questions"] = balanced
                            else:
                                parent["module_quiz"] = balanced
                            regenerated = True

            if not regenerated:
                return EduByteAIResponse(
                    response_type=ResponseType.FOLLOW_UP,
                    message="Generated quiz failed validation and automatic recovery.",
                    payload=FollowUpPayload(
                        response_type=ResponseType.FOLLOW_UP,
                        clarification_text=f"Quiz validation failed: {reason}",
                    ),
                )

        return EduByteAIResponse.model_validate(parsed_content)
