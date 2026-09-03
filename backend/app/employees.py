from sqlmodel import Session, select

from app.models import Employee


def get_or_seed_employee(db: Session) -> Employee:
    employee = db.exec(select(Employee)).first()
    if employee is not None:
        return employee

    employee = Employee(name="Jordan Lee")
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee
