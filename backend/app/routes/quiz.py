from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import QuizSubmission, User
from app.routes.auth import get_current_user
from app.schemas.schemas import QuizSubmissionRequest, QuizSubmissionResponse
from app.services.persistence import PASSING_SCORE, get_next_module, require_owned_module, upsert_progress

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/submit", response_model=QuizSubmissionResponse)
def submit_quiz(
    payload: QuizSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuizSubmissionResponse:
    module = require_owned_module(db, current_user, payload.module_id)
    questions = module.module_quiz or []
    if not questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module does not have a quiz")

    answer_key = {
        int(question["question_id"]): question.get("correct_option")
        for question in questions
        if isinstance(question, dict) and question.get("question_id") is not None
    }
    if not answer_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module quiz is not scorable")

    correct_count = sum(
        1
        for question_id, correct_option in answer_key.items()
        if payload.user_answers.get(question_id) == correct_option
    )
    total_questions = len(answer_key)
    score = round((correct_count / total_questions) * 100)
    passed = score >= PASSING_SCORE

    db.add(
        QuizSubmission(
            user_id=current_user.id,
            module_id=module.id,
            answers_json={str(key): value for key, value in payload.user_answers.items()},
            score=score,
            passed=passed,
        )
    )
    progress = upsert_progress(
        db,
        user_id=current_user.id,
        module_id=module.id,
        status="PASSED" if passed else "IN_PROGRESS",
        quiz_score=score,
        increment_attempts=True,
    )

    unlocked_module_id = None
    next_action = "Review the module and retry the quiz."
    if passed:
        next_module = get_next_module(db, module)
        if next_module:
            next_progress = upsert_progress(
                db,
                user_id=current_user.id,
                module_id=next_module.id,
                status="UNLOCKED",
            )
            unlocked_module_id = next_progress.module_id
            next_action = "Next module unlocked."
        else:
            next_action = "Course completed."

    db.commit()
    db.refresh(progress)
    return QuizSubmissionResponse(
        score=score,
        passed=passed,
        next_action=next_action,
        correct_count=correct_count,
        total_questions=total_questions,
        unlocked_module_id=unlocked_module_id,
    )
