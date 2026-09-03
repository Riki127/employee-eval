from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/employee_eval"
    session_question_count: int = 5


settings = Settings()
