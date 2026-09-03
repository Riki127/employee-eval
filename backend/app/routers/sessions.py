from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.ai import AIProvider, get_ai_provider
from app.db import get_session
from app.employees import get_or_seed_employee
from app.models import Evaluation, QAPair, Role, AssessmentSession, SessionStatus
from app.config import settings
from app.schemas import AnswerRequest, AnswerResponse, QAPairRead, SessionRead, SessionStartResponse, StartSessionRequest

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionStartResponse)
def start_session(
    body: StartSessionRequest,
    db: Session = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> SessionStartResponse:
    employee = get_or_seed_employee(db)
    existing_roles = list(db.exec(select(Role)).all())
    try:
        match = provider.match_or_create_role(body.role_title, existing_roles)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI provider failed to resolve role") from exc

    if match.matched_role_id is not None:
        role = db.get(Role, match.matched_role_id)
        if role is None:
            raise HTTPException(status_code=502, detail="AI provider returned an unknown role")
    else:
        role = Role(title=body.role_title, rubric=match.rubric.model_dump())
        db.add(role)
        db.commit()
        db.refresh(role)

    session = AssessmentSession(employee_id=employee.id, role_id=role.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        question = provider.generate_next_question(role, [])
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI provider failed to generate a question") from exc
    qa = QAPair(session_id=session.id, order=0, question=question.question)
    db.add(qa)
    db.commit()

    return SessionStartResponse(session_id=session.id, role_id=role.id, question=question.question)


@router.post("/{session_id}/answer", response_model=AnswerResponse)
def submit_answer(
    session_id: int,
    body: AnswerRequest,
    db: Session = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> AnswerResponse:
    session = db.get(AssessmentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == SessionStatus.completed:
        raise HTTPException(status_code=409, detail="Session already completed")

    qa_pairs = list(
        db.exec(select(QAPair).where(QAPair.session_id == session_id).order_by(QAPair.order)).all()
    )
    if not qa_pairs:
        raise HTTPException(status_code=500, detail="Session has no questions yet")
    current_qa = qa_pairs[-1]
    current_qa.answer = body.answer
    db.add(current_qa)
    db.commit()

    role = db.get(Role, session.role_id)
    if role is None:
        raise HTTPException(status_code=500, detail="Role not found for session")

    if len(qa_pairs) >= settings.session_question_count:
        try:
            evaluation_result = provider.evaluate_session(role, qa_pairs)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="AI provider failed to evaluate the session") from exc

        evaluation = Evaluation(
            session_id=session.id,
            verdict=evaluation_result.verdict,
            rationale=evaluation_result.rationale,
            recommendation=evaluation_result.recommendation,
        )
        db.add(evaluation)
        session.status = SessionStatus.completed
        session.completed_at = datetime.utcnow()
        db.add(session)
        db.commit()

        return AnswerResponse(
            status="completed",
            verdict=evaluation_result.verdict.value,
            rationale=evaluation_result.rationale,
            recommendation=evaluation_result.recommendation,
        )

    try:
        next_question = provider.generate_next_question(role, qa_pairs)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI provider failed to generate a question") from exc
    next_qa = QAPair(session_id=session.id, order=len(qa_pairs), question=next_question.question)
    db.add(next_qa)
    db.commit()

    return AnswerResponse(status="in_progress", question=next_question.question)


@router.get("/{session_id}", response_model=SessionRead)
def get_session_detail(session_id: int, db: Session = Depends(get_session)) -> SessionRead:
    session = db.get(AssessmentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    role = db.get(Role, session.role_id)
    if role is None:
        raise HTTPException(status_code=500, detail="Role not found for session")

    qa_pairs = list(
        db.exec(select(QAPair).where(QAPair.session_id == session_id).order_by(QAPair.order)).all()
    )
    evaluation = db.exec(select(Evaluation).where(Evaluation.session_id == session_id)).first()

    return SessionRead(
        id=session.id,
        status=session.status.value,
        role_title=role.title,
        qa_pairs=[QAPairRead(order=qa.order, question=qa.question, answer=qa.answer) for qa in qa_pairs],
        verdict=evaluation.verdict.value if evaluation else None,
        rationale=evaluation.rationale if evaluation else None,
        recommendation=evaluation.recommendation if evaluation else None,
    )
