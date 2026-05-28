import json
import os
from typing import Any, Dict, List

from groq import Groq

from app.schemas.schemas import EduByteAIResponse, ResponseType


GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else Groq()

SYSTEM_PROMPT = """
You are the hyper-intelligent core engine of EduByte AI, an adaptive learning assistant built for Nigerian students preparing for curriculum-driven exams (WAEC, JAMB, NECO).

### INPUT FORMAT
You will receive an execution payload containing:
1. Full Conversation History (Chat records mapping past interactions).
2. The New Client Message (The latest instruction or query from the student).

### DECISION TREE & CONFLICT RESOLUTION RULES
Analyze the intent of the latest message against past history and execute EXACTLY one path:
- RULE 1 (Conflict Resolution): If the user asks for BOTH a Course and a Quiz at the same time, you MUST select 'COURSE_GENERATION'. Each module within the course automatically contains an embedded 10-question quiz, satisfying both requirements.
- RULE 2 (Missing Context Gating): If the user requests a course or quiz but omits critical context (e.g., does not state the topic), select 'FOLLOW_UP'. Do not ask redundant questions. If the request is clear enough to infer defaults, proceed directly to content creation.
- RULE 3 (Standalone Assessment): If the user specifically asks to be tested on an isolated topic, select 'PRACTICE_QUIZ'.
- RULE 4 (General Conversations/Isolated Queries): If the user says hello, asks a broad trivia question, or engages in casual chat that doesn't demand a full learning path or test, select 'GENERAL_QUESTION_ANSWER'.

### OUTPUT FORMAT STRUCTURAL REQUIREMENT
You must output a single, tightly formatted JSON object adhering completely to the schemas below. Do not append conversational preambles or postscripts outside the JSON structure.

---

### STRUCTURAL SCHEMAS & EXAMPLES PER RESPONSE TYPE

#### TYPE 1: FOLLOW_UP
- Use Case: Crucial missing details.
- JSON Shape:
{
  "response_type": "FOLLOW_UP",
  "message": "I'm ready to set up your study session! Just need one quick detail.",
  "payload": {
    "clarification_text": "Which exam format are you targeting for this Economics topic? WAEC or JAMB?"
  }
}

#### TYPE 2: GENERAL_QUESTION_ANSWER
- Use Case: Greetings, explanations, short queries.
- JSON Shape:
{
  "response_type": "GENERAL_QUESTION_ANSWER",
  "message": "Here is the explanation you requested.",
  "payload": {
    "answer": "The capital of Nigeria was moved from Lagos to Abuja on December 12, 1991, primarily due to Abuja's central geographical location and lower population density."
  }
}

#### TYPE 3: PRACTICE_QUIZ
- Use Case: Standalone assessment requests.
- Constraints: options list must contain exactly 4 strings without labels like 'A', 'B', etc. correct_option maps as A=index 0, B=index 1, C=index 2, D=index 3.
- JSON Shape:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Here is your practice quiz preparation block.",
  "payload": {
    "quiz_title": "JAMB Physics: Linear Momentum Mock",
    "subject": "Physics",
    "questions": [
      {
        "question_id": 1,
        "question_text": "What is the SI unit of impulse?",
        "options": ["Newton seconds", "Joules", "Watts", "Kilograms per meter"],
        "correct_option": "A"
      }
    ]
  }
}

#### TYPE 4: COURSE_GENERATION
- Use Case: Comprehensive roadmap creation.
- Constraints: Every module generated MUST include a 'module_quiz' containing exactly 10 multi-choice questions mapped to that module's content. Subtopics must use markdown formatting.
- JSON Shape:
{
  "response_type": "COURSE_GENERATION",
  "message": "I have successfully compiled your comprehensive course layout mapped to the NERDC syllabus.",
  "payload": {
    "course_title": "Introduction to Web Development with Python",
    "subject": "Computer Science",
    "modules": [
      {
        "module_title": "Module 1: Foundations of Backend Execution",
        "subtopics": [
          {
            "title": "Definition of a Server",
            "content_markdown": "A server is a software system that processes incoming network requests. In Python, frameworks like **FastAPI** map functions to web endpoints.",
            "examples": ["An API endpoint routing HTTP GET requests to retrieve user database items."]
          }
        ],
        "module_quiz": [
          {
            "question_id": 1,
            "question_text": "Which Python framework is best optimized for high-performance asynchronous API execution?",
            "options": ["Django", "Flask", "FastAPI", "Bottle"],
            "correct_option": "C"
          }
        ]
      }
    ]
  }
}
""".strip()


class AIEngineService:
    @staticmethod
    def format_history_context(history_meta: List[Dict[str, Any]], current_message: str) -> str:
        """
        Combines historical text structures and current prompt inputs into a unified,
        highly linear conversational context window block to guarantee flawless memory retention.
        """
        context_block = "CONVERSATION HISTORY RECORDS:\n"

        for turn in history_meta:
            role = "User" if turn.get("role") == "user" else "EduByteAI"
            content = turn.get("content", "")
            context_block += f"[{role}]: {content}\n"

        context_block += f"\nNEW CLIENT CURRENT UTTERANCE: '{current_message}'\n"
        context_block += "Execute analysis against the system directive constraints and respond with the requested structured layout."
        return context_block

    @staticmethod
    def _normalize_response_content(raw_content: str) -> Dict[str, Any]:
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError("Groq response was not valid JSON.") from exc

    @staticmethod
    def _normalize_payload_structure(parsed_content: Dict[str, Any]) -> Dict[str, Any]:
        response_type = parsed_content.get("response_type")
        payload = parsed_content.get("payload")

        if response_type == ResponseType.COURSE_GENERATION.value and isinstance(payload, dict):
            modules = payload.get("modules", [])
            if isinstance(modules, list):
                for module in modules:
                    if not isinstance(module, dict):
                        continue
                    subtopics = module.get("subtopics", [])
                    if not isinstance(subtopics, list):
                        continue
                    for subtopic in subtopics:
                        if not isinstance(subtopic, dict):
                            continue
                        if "examples" not in subtopic and "example" in subtopic:
                            example_value = subtopic.pop("example")
                            if isinstance(example_value, list):
                                subtopic["examples"] = example_value
                            elif example_value is None:
                                subtopic["examples"] = []
                            else:
                                subtopic["examples"] = [example_value]

        return parsed_content

    @classmethod
    async def process_user_intent(cls, current_message: str, history_meta: List[Dict[str, Any]]) -> EduByteAIResponse:
        """
        Orchestrates full context assembly and forces Groq into an immutable
        structured JSON mapping using the Pydantic schema validation pipeline.
        """
        compiled_contents = cls.format_history_context(history_meta, current_message)

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": compiled_contents},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            raw_content = response.choices[0].message.content or "{}"
            parsed_content = cls._normalize_response_content(raw_content)
            parsed_content = cls._normalize_payload_structure(parsed_content)
            return EduByteAIResponse.model_validate(parsed_content)

        except Exception:
            return EduByteAIResponse(
                response_type=ResponseType.FOLLOW_UP,
                message="I encountered a slight sorting glitch mapping out that request structure. Could you clarify your topic or specify the exact exam context again?",
                payload={
                    "clarification_text": "Please provide a bit more detail regarding your current learning objective or target subject syllabus."
                },
            )