from enum import Enum
from typing import List, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field, ConfigDict

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

# --- Option A: AI Needs Clarification ---
class FollowUpPayload(BaseModel):
    clarification_text: str = Field(..., description="The highly contextual question asking for necessary exam/topic parameters")

# --- Option B: AI Generates Full Course Outline & Content ---
class SubTopicContent(BaseModel):
    title: str = Field(..., description="Subtopic title")
    content_markdown: str = Field(..., description="Deep textbook-style content, explanations, and key rules")
    examples: List[str] = Field(..., description="Real-world practical examples or worked mathematical proofs relevant to the topic")

class CourseModule(BaseModel):
    module_title: str = Field(..., description="Name of the core module chapter")
    subtopics: List[SubTopicContent] = Field(..., description="List of granular breakdowns within this module")

class CourseGenerationPayload(BaseModel):
    course_title: str = Field(..., description="The unified master title of the generated roadmap")
    subject: str = Field(..., description="The overriding academic category (e.g., Further Mathematics, JAMB Chemistry)")
    modules: List[CourseModule] = Field(..., description="Structured hierarchical timeline of learning modules")
    estimated_minutes: int = Field(..., description="Total time budget needed to process this concept framework")

# --- Option C: AI Generates An Interactive Assessment Gate ---
class QuizQuestion(BaseModel):
    question_id: int = Field(..., description="Chronological sequence index")
    question_text: str = Field(..., description="The actual problem vector definition")
    options: Dict[str, str] = Field(..., description="A dictionary map of choices. Must explicitly be keys: A, B, C, D")
    correct_option: Literal["A", "B", "C", "D"] = Field(..., description="The exact correct key mapping parameter")

class PracticeQuizPayload(BaseModel):
    quiz_title: str = Field(..., description="The specific tracking assessment module header name")
    subject: str = Field(...)
    questions: List[QuizQuestion] = Field(..., description="List of 10 to 20 structured quiz arrays")

# --- Universal Unified Wrapper using Pydantic Discriminator ---
class EduByteAIResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    response_type: ResponseType = Field(..., description="Determines which structural model layout is being evaluated")
    message: str = Field(..., description="General fallback conversational text for the chat interface interface layer")
    
    # Polymorphic nested blocks based on the evaluation choice made above
    payload: Union[FollowUpPayload, CourseGenerationPayload, PracticeQuizPayload] = Field(..., description="The validated machine-readable nested payload tracking data execution contracts")

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