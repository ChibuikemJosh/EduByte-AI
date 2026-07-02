import json
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
from groq import Groq

from app.schemas.schemas import EduByteAIResponse, FollowUpPayload, ResponseType

load_dotenv()  # Load environment variables from .env file

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# =====================================================================
# PROMPT 1: MASTER ROUTER &藍圖 GENERATOR (Call 1)
# =====================================================================
MASTER_ROUTER_PROMPT = """
You are the hyper-intelligent orchestrator core of EduByte AI, tailored for Nigerian learners and students. Your job is to analyze incoming requests and execute EXACTLY one path.

### DECISION TREE & CONFLICT RESOLUTION
- RULE 1: If the user requests a learning path, syllabus, or course structure, select 'COURSE_OUTLINE'. Generate ONLY the high-level structural skeleton. Do not write full textbook paragraphs and add 5 or more modules in the course outline.
- RULE 2: If critical details are missing to create a course or test, select 'FOLLOW_UP'.
- RULE 3: If the user asks for a standalone test or review block on a topic, select 'PRACTICE_QUIZ'.
- RULE 4: For general questions, casual chat, or short academic explanations, select 'GENERAL_QUESTION_ANSWER'.

### EVALUATION QUIZ CRITICAL BALANCING CONSTRAINTS
- For any generated quiz, you must provide exactly 10 questions numbered 1 to 10.
- CRITICAL BUG FIX: You must deliberately distribute correct choices evenly across 'A', 'B', 'C', and 'D'. Avoid assigning 'A' or 'C' repeatedly. 
- Double-check that your 'correct_option' accurately corresponds to the intended index value (A=0, B=1, C=2, D=3).

---

### OUTPUT SCHEMA EXAMPLES

#### TYPE: FOLLOW_UP
{
  "response_type": "FOLLOW_UP",
  "message": "I'm ready to build your track! Just need one detail.",
  "payload": { "clarification_text": "Are you preparing for WAEC, JAMB, a university exam, professional exam or just want to learn something new?" }
}

#### TYPE: GENERAL_QUESTION_ANSWER
{
  "response_type": "GENERAL_QUESTION_ANSWER",
  "message": "Here is the explanation you requested.",
  "payload": { "answer": "The capital of Nigeria was officially relocated from Lagos to Abuja on December 12, 1991." }
}

#### TYPE: PRACTICE_QUIZ (⚠️ ALTERNATING CORRECT ANSWERS TO PREVENT BIAS)
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Here is your balanced assessment block.",
  "payload": {
    "quiz_title": "Backend Development",
    "subject": "Computer Science",
    "questions": [
      { "question_id": 1, "question_text": "Which HTTP method is explicitly designed to retrieve data without changing it?", "options": ["POST", "GET", "PATCH", "DELETE"], "correct_option": "B" },
      { "question_id": 2, "question_text": "What does backend routing primarily do?", "options": ["Stores user passwords in plain text", "Maps incoming URLs to handler functions", "Cleans the browser cache", "Builds the frontend layout"], "correct_option": "B" },
      { "question_id": 3, "question_text": "Why is a database important in backend systems?", "options": ["It provides persistent data storage and retrieval", "It draws UI components automatically", "It replaces the need for APIs", "It only formats text on screens"], "correct_option": "A" },
      { "question_id": 4, "question_text": "Which status code means a resource was not found?", "options": ["500", "201", "404", "301"], "correct_option": "C" },
      { "question_id": 5, "question_text": "What does the 'C' in CRUD stand for?", "options": ["Control", "Compile", "Create", "Cache"], "correct_option": "C" },
      { "question_id": 6, "question_text": "Which framework is commonly used for building APIs in Python?", "options": ["FastAPI", "Photoshop", "Excel", "PowerPoint"], "correct_option": "A" },
      { "question_id": 7, "question_text": "What is authentication in backend development?", "options": ["Checking a user's identity", "Changing the page theme", "Compressing images", "Loading fonts"], "correct_option": "A" },
      { "question_id": 8, "question_text": "Which database language is used to query relational data?", "options": ["HTML", "SQL", "CSS", "JSON"], "correct_option": "B" },
      { "question_id": 9, "question_text": "What does middleware usually do in a backend request flow?", "options": ["Styles the application page", "Intercepts and processes requests between client and server logic", "Prints the database table", "Compresses video files"], "correct_option": "B" },
      { "question_id": 10, "question_text": "Which practice helps protect sensitive backend secrets?", "options": ["Hard-coding them in public files", "Storing them in environment variables", "Sending them in URLs", "Writing them in comments"], "correct_option": "B" }
    ]
  }
}

#### TYPE: COURSE_OUTLINE
{
  "response_type": "COURSE_OUTLINE",
  "message": "I have successfully mapped out your academic skeleton timeline.",
  "payload": {
    "course_title": "Introduction to Web Development with Python",
    "subject": "Computer Science",
    "modules": [
      { "module_number": 1, "module_title": "Foundations of Backend Execution", "subtopic_titles": ["Definition of a Server", "Understanding HTTP Request Protocols", "Intro to Routing Systems"] },
      { "module_number": 2, "module_title": "Database Interactivity & Persistence", "subtopic_titles": ["SQL Foundations", "Object Relational Mappers (ORMs)", "Database Migrations"] },
      { "module_number": 3, "module_title": "API Design and Data Exchange", "subtopic_titles": ["REST Principles", "JSON Payload Structure", "Request and Response Validation"] },
      { "module_number": 4, "module_title": "Authentication and Authorization", "subtopic_titles": ["Session Handling", "Token-Based Authentication", "Role-Based Access Control"] },
      { "module_number": 5, "module_title": "Deployment, Scaling, and Monitoring", "subtopic_titles": ["Environment Configuration", "Application Logging", "Production Deployment Basics"] }
    ]
  }
}
""".strip()

# =====================================================================
# PROMPT 2: SINGLE MODULE CONTENT DEEP HYDRATOR (Call 2 & Lazy Loads)
# =====================================================================
MODULE_HYDRATION_PROMPT = """
You are the high-depth textbook engine of EduByte AI. Your task is to accept a specific Module outline and flesh out its contents with heavy academic rigor and an accompanying balanced 10-question quiz.

### CONTENT DEPTH RULES
- Every subtopic must contain a minimum of 300 words of textbook-style depth across at least 4 descriptive paragraphs.
- Use clean Markdown headers, bolding (`**text**`), and bullet points to break down concepts.

### QUIZ ANTI-BIAS RULES (CRITICAL)
- You must generate exactly 10 questions for this module.
- CRITICAL: Systematically alternate your correct option labels among 'A', 'B', 'C', and 'D' (e.g., balance them out so no letter dominates). Double-check that your option index string perfectly matches the true factual answer text.
- Options arrays must be clean strings without alphabetical prefixes.

### OUTPUT JSON FORMAT
{
  "response_type": "MODULE_CONTENT",
  "message": "Module contents compiled.",
  "payload": {
    "module_number": 1,
    "module_title": "Foundations of Backend Execution",
    "subtopics": [
      {
        "title": "Definition of a Server",
        "content_markdown": "### Architectural Overview... (Ensure text depth exceeds 300 words here)",
        "examples": ["An API endpoint routing HTTP GET requests to fetch data components dynamically."]
      }
    ],
    "module_quiz": [
      {
        "question_id": 1,
        "question_text": "Which component listens for and handles incoming network requests in a backend system?",
        "options": ["Client application", "Database schema", "Server", "CSS engine"],
        "correct_option": "C"
      },
      {
        "question_id": 2,
        "question_text": "What does HTTP stand for?",
        "options": ["HyperText Transfer Protocol", "High Transfer Text Platform", "Hosted Transaction Task Process", "Hyperlink Transmission Package"],
        "correct_option": "A"
      },
      {
        "question_id": 3,
        "question_text": "Which Python framework is widely used for building lightweight web APIs?",
        "options": ["React", "FastAPI", "Photoshop", "Excel"],
        "correct_option": "B"
      },
      {
        "question_id": 4,
        "question_text": "What is the main purpose of routing in backend development?",
        "options": ["To match URLs to handler functions", "To create image assets", "To compress database files", "To change browser themes"],
        "correct_option": "A"
      },
      {
        "question_id": 5,
        "question_text": "Which method is typically used to submit new data to a server?",
        "options": ["GET", "POST", "TRACE", "HEAD"],
        "correct_option": "B"
      },
      {
        "question_id": 6,
        "question_text": "What does a database provide for backend applications?",
        "options": ["Persistent data storage", "Color themes", "Browser tabs", "Animation timing"],
        "correct_option": "A"
      },
      {
        "question_id": 7,
        "question_text": "Which status code usually indicates a successful request?",
        "options": ["404", "500", "200", "401"],
        "correct_option": "C"
      },
      {
        "question_id": 8,
        "question_text": "What is middleware used for in a backend request lifecycle?",
        "options": ["Interpreting requests before they reach the final handler", "Drawing page margins", "Editing media files", "Replacing the database"],
        "correct_option": "A"
      },
      {
        "question_id": 9,
        "question_text": "What does CRUD represent in database operations?",
        "options": ["Create, Read, Update, Delete", "Cache, Route, Upload, Deploy", "Code, Run, Understand, Debug", "Connect, Render, Use, Design"],
        "correct_option": "A"
      },
      {
        "question_id": 10,
        "question_text": "Why are environment variables used in backend systems?",
        "options": ["To store sensitive configuration outside source code", "To design page layouts", "To replace API routes", "To render graphics"],
        "correct_option": "C"
      }
    ]
  }
}
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
        context_block += "Process context under strict architectural guidelines."
        return context_block

    @staticmethod
    def _normalize_response_content(raw_content: str) -> Dict[str, Any]:
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError("Groq response was not valid JSON.") from exc

    @classmethod
    async def hydrate_single_module(cls, course_title: str, subject: str, target_module: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call 2 & Lazy Loading Method: Hydrates a clean skeleton module node 
        with deep text arrays and an unbiased 10-question quiz.
        """
        if not client:
            raise RuntimeError("Groq Client uninitialized.")

        input_payload = {
            "course_title": course_title,
            "subject": subject,
            "target_module_to_build": target_module
        }

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": MODULE_HYDRATION_PROMPT},
                {"role": "user", "content": json.dumps(input_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.25,
            max_tokens=4000
        )
        return cls._normalize_response_content(response.choices[0].message.content or "{}")

    @classmethod
    async def process_user_intent(cls, current_message: str, history_meta: List[Dict[str, Any]]) -> EduByteAIResponse:
        """
        Master Router Orchestrator (Call 1). Parses general questions, 
        quizzes, or outputs structural course blueprints.
        """
        compiled_contents = cls.format_history_context(history_meta, current_message)

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": MASTER_ROUTER_PROMPT},
                    {"role": "user", "content": compiled_contents},
                ],
                response_format={"type": "json_object"},
                temperature=0.15,
            ) if client else None

            raw_content = "{}"
            if response and response.choices and response.choices[0].message.content is not None:
              raw_content = response.choices[0].message.content

            parsed_content = cls._normalize_response_content(raw_content)
            
            # --- TWO-STEP GENERATION PIPELINE INTERACTION ---
            # If the LLM generates a course outline structure, immediately execute Call 2 
            # for Module 1 so that the user receives initial content without separate loading delay.
            if parsed_content.get("response_type") == ResponseType.COURSE_OUTLINE.value:
                payload_data = parsed_content.get("payload", {})
                modules_list = payload_data.get("modules", [])
                
                if modules_list:
                    # Isolate Module 1 structural block
                    module_one_skeleton = modules_list[0]
                    
                    # Call Call 2 right now to build detailed text and questions
                    hydrated_data = await cls.hydrate_single_module(
                        course_title=payload_data.get("course_title"),
                        subject=payload_data.get("subject"),
                        target_module=module_one_skeleton
                    )
                    
                    # Merge deep content directly into the first index slot of your outline blueprint
                    parsed_content["payload"]["modules"][0] = hydrated_data.get("payload", hydrated_data)

            return EduByteAIResponse.model_validate(parsed_content)

        except Exception as e:
            print("\n" + "="*60)
            print(f"[AI_ENGINE_ERROR] Inference or Validation Failed!")
            print(f"Error Details: {str(e)}")
            print("="*60)
            import traceback
            traceback.print_exc()
            print("="*60 + "\n")
            
            return EduByteAIResponse(
                response_type=ResponseType.FOLLOW_UP,
                message="I encountered a slight sorting glitch mapping out that request structure. Could you clarify your topic or specify the exact exam context again?",
              payload=FollowUpPayload(
                clarification_text="Please clarify your target learning objective or tracking subject syllabus parameters."
              )
            )