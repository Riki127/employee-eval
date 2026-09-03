from fastapi import FastAPI

from app.db import create_db_and_tables

app = FastAPI(title="Employee Eval POC")


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
