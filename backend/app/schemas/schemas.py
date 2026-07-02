from enum import Enum
from typing import List, Dict, Optional, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator, EmailStr

# =====================================================================
# 1. AUTHENTICATION SCHEMAS
# =====================================================================

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["chy_codes"])
    # 💡 UPGRADE: Uses EmailStr for native automated format validation
    email: EmailStr = Field(..., examples=["chidi@edubyte.ng"])
    phone_number: Optional[str] = Field(None, description="International format, e.g., +2348012345678", examples=["+2348012345678"])
    password: str = Field(..., min_length=6, description="Raw password to be hashed by the backend")

class UserLoginRequest(BaseModel):
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
    COURSE_OUTLINE = "COURSE_OUTLINE"      # 💡 NEW: Step 1 Blueprint
    MODULE_CONTENT = "MODULE_CONTENT"      # 💡 NEW: Step 2 Lazy-loaded content block
    PRACTICE_QUIZ = "PRACTICE_QUIZ"
    GENERAL_QUESTION_ANSWER = "GENERAL_QUESTION_ANSWER"

# --- Option A: AI Needs Clarification ---
class FollowUpPayload(BaseModel):
    response_type: Literal[ResponseType.FOLLOW_UP] = Field(ResponseType.FOLLOW_UP, description="Explicitly identifies this payload as a follow-up request")
    clarification_text: str = Field(..., description="The highly contextual question asking for necessary exam/topic parameters")

# --- Common Reusable Core Components ---
class QuizQuestion(BaseModel):
    question_id: int = Field(..., description="Serial index of the question (e.g., 1, 2, 3...)")
    question_text: str = Field(..., description="The problem or question being asked")
    options: List[str] = Field(..., min_length=4, max_length=4, description="List of exactly 4 choices (strings only)")
    correct_option: Literal["A", "B", "C", "D"] = Field(..., description="A=Index 0, B=Index 1, C=Index 2, D=Index 3")

class SubTopicContent(BaseModel):
    title: str = Field(..., description="Subtopic title")
    content_markdown: str = Field(..., description="Deep textbook-style content, explanations, and key rules")
    examples: List[str] = Field(default_factory=list, description="Real-world practical examples")

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

# --- 💡 NEW Option B: Call 1 Blueprint Structure (Syllabus Architecture) ---
class ModuleOutline(BaseModel):
    module_number: int = Field(..., description="Sequence placement identifier")
    module_title: str = Field(..., description="High-level title of the module segment")
    subtopic_titles: List[str] = Field(..., description="Simple array of text titles to build the structural skeleton layout")

# --- 💡 NEW Option C: Call 2 + Lazy Loading Content Blocks ---
class ModuleContentPayload(BaseModel):
    response_type: Literal[ResponseType.MODULE_CONTENT] = Field(ResponseType.MODULE_CONTENT, description="Explicitly identifies this payload as a module content block")
    module_number: int = Field(..., description="Identifies which structural node this content hydrator belongs to")
    module_title: str = Field(..., description="Name of the core module chapter")
    subtopics: List[SubTopicContent] = Field(..., description="Deep text-filled paragraphs")
    module_quiz: List[QuizQuestion] = Field(..., min_length=10, max_length=10, description="Strictly 10 questions")

class CourseOutlinePayload(BaseModel):
    response_type: Literal[ResponseType.COURSE_OUTLINE] = Field(ResponseType.COURSE_OUTLINE, description="Explicitly identifies this payload as a course outline blueprint")
    course_title: str = Field(..., description="Master title of the generated course roadmap")
    subject: str = Field(..., description="The category domain profile classification")
    # 💡 ALLOW EITHER SKELETON OR FULLY HYDRATED MODULES IN THE LIST
    modules: List[Union[ModuleOutline, ModuleContentPayload]] = Field(..., description="The skeleton outline framework mapping")

# --- Option D: Standalone Assessments ---
class PracticeQuizPayload(BaseModel):
    response_type: Literal[ResponseType.PRACTICE_QUIZ] = Field(ResponseType.PRACTICE_QUIZ, description="Explicitly identifies this payload as a practice quiz")
    quiz_title: str = Field(..., description="The specific tracking assessment module header name")
    subject: str = Field(...)
    questions: List[QuizQuestion] = Field(..., min_length=10, max_length=10, description="Strictly 10 questions")

# --- Option E: General Explanations or Greetings ---
class GeneralQuestionPayload(BaseModel):
    response_type: Literal[ResponseType.GENERAL_QUESTION_ANSWER] = Field(ResponseType.GENERAL_QUESTION_ANSWER, description="Explicitly identifies this payload as a general question answer")
    answer: str = Field(..., description="The conversational answer or academic explanation")

# --- Universal Unified Wrapper using Explicit Pydantic Discriminator ---
class EduByteAIResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    response_type: ResponseType = Field(..., description="Determines which structural model layout is being evaluated")
    message: str = Field(..., description="General fallback conversational text for the user interface layout layer")
    
    # 💡 UPGRADE: Explicit discriminator allows blazing-fast lookups based on the 'response_type' value
    payload: Union[
        FollowUpPayload, 
        CourseOutlinePayload, 
        ModuleContentPayload, 
        PracticeQuizPayload, 
        GeneralQuestionPayload
    ] = Field(..., discriminator="response_type")

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