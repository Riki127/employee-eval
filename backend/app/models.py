from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class Verdict(str, Enum):
    below = "below"
    meeting = "meeting"
    exceeding = "exceeding"


class SessionStatus(str, Enum):
    in_progress = "in_progress"
    completed = "completed"


class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    rubric: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class AssessmentSession(SQLModel, table=True):
    __tablename__ = "session"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employee.id")
    role_id: int = Field(foreign_key="role.id")
    status: SessionStatus = Field(default=SessionStatus.in_progress)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class QAPair(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="session.id")
    order: int
    question: str
    answer: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Evaluation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="session.id", unique=True)
    verdict: Verdict
    rationale: str
    recommendation: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
