import psycopg
import pytest
from psycopg import errors as psycopg_errors
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

TEST_DB_NAME = "employee_eval_test"
_admin_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
_test_url = settings.database_url.rsplit("/", 1)[0] + f"/{TEST_DB_NAME}"


def _ensure_test_database_exists() -> None:
    conn = psycopg.connect(_admin_url, autocommit=True)
    try:
        conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    except psycopg_errors.DuplicateDatabase:
        pass
    finally:
        conn.close()


_ensure_test_database_exists()
engine = create_engine(_test_url, connect_args={"prepare_threshold": None})


@pytest.fixture()
def db_session() -> Session:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
