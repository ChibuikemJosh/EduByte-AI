import asyncio
import json
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
from groq import Groq

from app.schemas.schemas import EduByteAIResponse, FollowUpPayload, ResponseType

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# =====================================================================
# PROMPT 1: MASTER ROUTER & BLUEPRINT GENERATOR
# =====================================================================
MASTER_ROUTER_PROMPT = """
You are the hyper-intelligent orchestrator core of EduByte AI, tailored for Nigerian learners. Your job is to analyze incoming requests and execute EXACTLY one path.

### DECISION TREE & CONFLICT RESOLUTION
- RULE 1: If the user requests a learning path, syllabus, or course structure, select 'COURSE_OUTLINE'. Generate ONLY the high-level structural skeleton. Do not write full textbook paragraphs and add 5 or more modules in the course outline.
- RULE 2: If critical details are missing to create a course or test, select 'FOLLOW_UP'.
- RULE 3: If the user asks for a standalone test or review block on a topic, select 'PRACTICE_QUIZ'.
- RULE 4: For general questions, casual chat, or short academic explanations, select 'GENERAL_QUESTION_ANSWER'.

---
### OUTPUT SCHEMA EXAMPLES

#### TYPE: COURSE_OUTLINE
{
  "response_type": "COURSE_OUTLINE",
  "message": "I have successfully mapped out your academic skeleton timeline.",
  "payload": {
    "course_title": "Introduction to Web Development with Python",
    "subject": "Computer Science",
    "modules": [
      { "module_number": 1, "module_title": "Foundations of Backend Execution", "subtopic_titles": ["Definition of a Server", "Understanding HTTP Request Protocols", "Intro to Routing Systems"] },
      { "module_number": 2, "module_title": "Database Interactivity & Persistence", "subtopic_titles": ["SQL Foundations", "Object Relational Mappers (ORMs)"] }
    ]
  }
}
""".strip()

# =====================================================================
# 💡 MICRO-PROMPT 2: SINGLE SUBTOPIC CONTENT GENERATOR
# =====================================================================
SUBTOPIC_CONTENT_PROMPT = """
You are the high-depth textbook parsing node of EduByte AI. Your role is to write a comprehensive textbook section for ONE specific subtopic. 
You are given the Master Module Title and a list of all accompanying subtopics to help you understand the architectural context and flow, but you must focus your core writing on the target subtopic.

### CONTENT DEPTH MANDATES
- Provide an extensive, exhaustive academic explanation for the target subtopic (minimum 350 words across 4 paragraphs).
- Use clear Markdown formatting headers, bold terms, and descriptive bullet lists.
- Provide a list of real-world code snippets or practical execution examples inside the `examples` array.

### OUTPUT JSON FORMAT
{
  "title": "Target Subtopic Name",
  "content_markdown": "### Conceptual Deep Dive...\\n\\nDetailed academic text here...",
  "examples": [
    "Example implementation step or code block sample configuration."
  ]
}
""".strip()

# =====================================================================
# 💡 MICRO-PROMPT 3: TARGETED MODULE ASSESSMENT BLOCK GENERATOR
# =====================================================================
QUIZ_GENERATION_PROMPT = """
You are the assessment engine of EduByte AI. Your task is to generate a rigorous, multi-option 10-question quiz explicitly matching a module and its subtopics.
You are provided with the conversation history and context records to ensure alignment with any previous explanations or specialized themes discussed with the user.

### QUIZ ANTI-BIAS RULES (CRITICAL MANDATE)
- You must generate exactly 10 questions, numbered sequentially from 1 to 10.
- 🚨 ANTI-BIAS ALGORITHM: You are FORBIDDEN from choosing the same letter for more than 3 answers across the entire quiz. Shuffling and alternating correct keys across the entire exam block is mandatory.
- Double-check that your 'correct_option' character explicitly maps to the exact index of your text array option string (A=Index 0, B=Index 1, C=Index 2, D=Index 3).
- Options arrays must be clean text choice strings without alphabetical prefixes like 'A)' or '1. '.

### OUTPUT JSON FORMAT
[
  {
    "question_id": 1,
    "question_text": "Which component manages data persistence layer requirements safely?",
    "options": ["Database management system", "Frontend layout wrapper", "CSS utility module", "Browser state cookie"],
    "correct_option": "A"
  }
]
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
    def _normalize_response_content(raw_content: str) -> Any:
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError("Groq response was not valid JSON.") from exc

    # =====================================================================
    # 💡 NEW MICRO-FUNCTION: Generates one isolated subtopic text section
    # =====================================================================
    @classmethod
    async def generate_subtopic_text_block(
        cls, module_title: str, all_subtopics: List[str], target_subtopic: str
    ) -> Dict[str, Any]:
        if not client:
            raise RuntimeError("Groq Client uninitialized.")

        input_payload = {
            "parent_module_title": module_title,
            "sibling_context_subtopics": all_subtopics,
            "target_subtopic_to_explain": target_subtopic
        }

        # Wrapping synchronous Groq call in asyncio.to_thread to maintain asynchronous performance
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SUBTOPIC_CONTENT_PROMPT},
                {"role": "user", "content": json.dumps(input_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.25,
            max_tokens=2000
        )
        return cls._normalize_response_content(response.choices[0].message.content or "{}")

    # =====================================================================
    # 💡 NEW MICRO-FUNCTION: Generates an isolated 10-question quiz array
    # =====================================================================
    @classmethod
    async def generate_isolated_quiz_block(
        cls, module_title: str, subtopic_titles: List[str], history_meta: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not client:
            raise RuntimeError("Groq Client uninitialized.")

        input_payload = {
            "module_title": module_title,
            "subtopics_covered": subtopic_titles,
            "historical_chat_context": history_meta
        }

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": QUIZ_GENERATION_PROMPT},
                {"role": "user", "content": json.dumps(input_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.15,
            max_tokens=3000
        )
        raw_data = cls._normalize_response_content(response.choices[0].message.content or "{}")
        # Ensure it returns the list array directly
        return raw_data.get("questions", raw_data) if isinstance(raw_data, dict) else raw_data

    # =====================================================================
    # MAIN COHESIVE SYSTEM FLOW INTERACTION ORCHESTRATOR
    # =====================================================================
    @classmethod
    async def process_user_intent(cls, current_message: str, history_meta: List[Dict[str, Any]]) -> EduByteAIResponse:
        compiled_contents = cls.format_history_context(history_meta, current_message)

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
            ) if client else None

            raw_content = "{}"
            if response and response.choices and response.choices[0].message.content is not None:
                raw_content = response.choices[0].message.content

            parsed_content = cls._normalize_response_content(raw_content)

            # ⚡️ THE ASYNC PARALLEL GATHER INTERACTION PIPELINE
            if parsed_content.get("response_type") == ResponseType.COURSE_OUTLINE.value:
                payload_data = parsed_content.get("payload", {})
                modules_list = payload_data.get("modules", [])

                if modules_list:
                    mod_one = modules_list[0]
                    m_title = mod_one.get("module_title")
                    subs = mod_one.get("subtopic_titles", [])

                    print(f"⚡️ [Orchestrator] Firing {len(subs)} Text and 1 Quiz generation tasks parallelly...")

                    # Step A: Queue up text generation tasks for all subtopics simultaneously
                    text_tasks = [cls.generate_subtopic_text_block(m_title, subs, s) for s in subs]
                    # Step B: Queue up the quiz task concurrently
                    quiz_task = cls.generate_isolated_quiz_block(m_title, subs, history_meta)

                    # Step C: Await execution using asyncio.gather
                    gathered_results = await asyncio.gather(*text_tasks, quiz_task)

                    completed_subtopics = gathered_results[:-1]
                    completed_quiz = gathered_results[-1]

                    # Step D: Construct the hydrated module dictionary matching ModuleContentPayload
                    hydrated_module_one = {
                        "response_type": ResponseType.MODULE_CONTENT.value,
                        "module_number": mod_one.get("module_number", 1),
                        "module_title": m_title,
                        "subtopics": completed_subtopics,
                        "module_quiz": completed_quiz
                    }

                    # Overwrite index 0 with the fully populated component structure
                    parsed_content["payload"]["modules"][0] = hydrated_module_one

            # Inject response discriminator values to satisfy Pydantic validations cleanly
            if "response_type" in parsed_content and "payload" in parsed_content:
                if isinstance(parsed_content["payload"], dict):
                    parsed_content["payload"]["response_type"] = parsed_content["response_type"]

            return EduByteAIResponse.model_validate(parsed_content)

        except Exception as e:
            print(f"\n❌ [AI_ENGINE_ERROR] Pipeline Failure: {str(e)}")
            import traceback
            traceback.print_exc()

            return EduByteAIResponse(
                response_type=ResponseType.FOLLOW_UP,
                message="I encountered an extraction error setting up your track paths. Could you clarify your syllabus details?",
                payload=FollowUpPayload(clarification_text="Please refine your targeted learning request.")
            )