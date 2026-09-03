from sqlmodel import Session

from app.employees import get_or_seed_employee


def test_get_or_seed_employee_creates_once(db_session: Session):
    first = get_or_seed_employee(db_session)
    second = get_or_seed_employee(db_session)

    assert first.id == second.id
    assert first.name == "Jordan Lee"
