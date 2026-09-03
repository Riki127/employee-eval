from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(settings.database_url, echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
