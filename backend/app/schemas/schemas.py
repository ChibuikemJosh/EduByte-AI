from enum import Enum
from typing import List, Dict, Optional, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

# =====================================================================
# 1. AUTHENTICATION SCHEMAS
# =====================================================================

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["chy_codes"])
    email: str = Field(..., examples=["chidi@edubyte.ng"])
    phone_number: Optional[str] = Field(None, description="International format, e.g., +2348012345678", examples=["+2348012345678"])
    password: str = Field(..., min_length=6, description="Raw password to be hashed by the backend")

class UserLoginRequest(BaseModel):
    # Flexible login allowing username, email, or WhatsApp phone number
    login_identifier: str = Field(..., description="Can be email, username, or WhatsApp phone number")
    password: str = Field(...)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

# =====================================================================
# 2. INBOUND CHAT & CORE REQUESTS
# =====================================================================

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique UUID for web sessions, or Phone Number for WhatsApp users")
    message: str = Field(..., description="The user's text prompt, query, or material command")

# =====================================================================
# 3. OUTBOUND POLYMORPHIC AI SCHEMAS (The Core Logic Engine)
# =====================================================================

class ResponseType(str, Enum):
    FOLLOW_UP = "FOLLOW_UP"
    COURSE_GENERATION = "COURSE_GENERATION"
    PRACTICE_QUIZ = "PRACTICE_QUIZ"
    GENERAL_QUESTION_ANSWER = "GENERAL_QUESTION_ANSWER"

# --- Option A: AI Needs Clarification ---
class FollowUpPayload(BaseModel):
    clarification_text: str = Field(..., description="The highly contextual question asking for necessary exam/topic parameters")

# --- Option B: AI Generates Full Course Outline & Content ---
class QuizQuestion(BaseModel):
    question_id: int = Field(..., description="Serial index of the question (e.g., 1, 2, 3...)")
    question_text: str = Field(..., description="The problem or question being asked")
    options: List[str] = Field(..., min_items=4, max_items=4, description="List of exactly 4 choices (strings only, do not include letters like A, B, C, D)")
    correct_option: Literal["A", "B", "C", "D"] = Field(..., description="A maps to index 0, B to index 1, C to index 2, D to index 3")

class SubTopicContent(BaseModel):
    title: str = Field(..., description="Subtopic title")
    content_markdown: str = Field(..., description="Deep textbook-style content, explanations, and key rules")
    examples: List[str] = Field(default_factory=list, description="Real-world practical examples or worked mathematical proofs relevant to the topic")

    @model_validator(mode="before")
    @classmethod
    def normalize_examples(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        if "examples" not in value and "example" in value:
            example_value = value.pop("example")
            if isinstance(example_value, list):
                value["examples"] = example_value
            elif example_value is None:
                value["examples"] = []
            else:
                value["examples"] = [example_value]

        return value

class CourseModule(BaseModel):
    module_title: str = Field(..., description="Name of the core module chapter")
    subtopics: List[SubTopicContent] = Field(..., description="List of granular breakdowns within this module")
    module_quiz: List[QuizQuestion] = Field(..., min_length=1, max_length=10, description="An embedded quiz to test understanding of this module")

class CourseGenerationPayload(BaseModel):
    course_title: str = Field(..., description="The unified master title of the generated roadmap")
    subject: str = Field(..., description="The overriding academic category (e.g., Further Mathematics, JAMB Chemistry)")
    modules: List[CourseModule] = Field(..., description="Structured hierarchical timeline of learning modules")

class PracticeQuizPayload(BaseModel):
    quiz_title: str = Field(..., description="The specific tracking assessment module header name")
    subject: str = Field(...)
    questions: List[QuizQuestion] = Field(..., min_length=1, description="List of structured quiz questions")

# --- Option D: General Explanations or Greetings ---
class GeneralQuestionPayload(BaseModel):
    answer: str = Field(..., description="The conversational answer or academic explanation provided by the AI")

# --- Universal Unified Wrapper using Pydantic Discriminator ---
class EduByteAIResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    response_type: ResponseType = Field(..., description="Determines which structural model layout is being evaluated")
    message: str = Field(..., description="General fallback conversational text for the chat interface interface layer")
    
    # Polymorphic nested blocks based on the evaluation choice made above
    payload: Union[FollowUpPayload, CourseGenerationPayload, PracticeQuizPayload, GeneralQuestionPayload] = Field(..., description="The validated machine-readable nested payload tracking data execution contracts")

# =====================================================================
# 4. PROGRESS & QUIZ SUBMISSION TRAFFIC SCHEMAS
# =====================================================================

class QuizSubmissionRequest(BaseModel):
    module_id: int = Field(...)
    user_answers: Dict[int, Literal["A", "B", "C", "D"]] = Field(..., description="Maps question_id to the user selected option string")

class QuizSubmissionResponse(BaseModel):
    score: int = Field(..., description="Calculated test score scaling out of 100 percentage parameters")
    passed: bool = Field(..., description="Identifies if the score matches passing index thresholds to allow progression")
    next_action: str = Field(..., description="System instructions telling frontend to either unlock the next graph node or serve a warning refresher block")