from fastapi import FastAPI

from app.db import create_db_and_tables
from app.routers import sessions

app = FastAPI(title="Employee Eval POC")


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(sessions.router)
