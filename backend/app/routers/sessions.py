from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.ai.mock import MockAIProvider
from app.db import get_session
from app.employees import get_or_seed_employee
from app.models import QAPair, Role, AssessmentSession
from app.schemas import SessionStartResponse, StartSessionRequest

router = APIRouter(prefix="/sessions", tags=["sessions"])
ai_provider = MockAIProvider()


@router.post("", response_model=SessionStartResponse)
def start_session(body: StartSessionRequest, db: Session = Depends(get_session)) -> SessionStartResponse:
    employee = get_or_seed_employee(db)
    existing_roles = list(db.exec(select(Role)).all())
    match = ai_provider.match_or_create_role(body.role_title, existing_roles)

    if match.matched_role_id is not None:
        role = db.get(Role, match.matched_role_id)
        assert role is not None
    else:
        role = Role(title=body.role_title, rubric=match.rubric.model_dump())
        db.add(role)
        db.commit()
        db.refresh(role)

    session = AssessmentSession(employee_id=employee.id, role_id=role.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    question = ai_provider.generate_next_question(role, [])
    qa = QAPair(session_id=session.id, order=0, question=question.question)
    db.add(qa)
    db.commit()

    return SessionStartResponse(session_id=session.id, role_id=role.id, question=question.question)
