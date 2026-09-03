from sqlmodel import Session

from app.models import Employee, Role


def test_role_and_employee_round_trip(db_session: Session):
    role = Role(
        title="Software Engineer",
        rubric={"current_tier_expectations": ["writes clean code"], "next_tier_expectations": ["leads projects"], "career_ladder_summary": "IC ladder"},
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    employee = Employee(name="Jordan Lee")
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    assert role.id is not None
    assert employee.id is not None
    assert role.rubric["current_tier_expectations"] == ["writes clean code"]
