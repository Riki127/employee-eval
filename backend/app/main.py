from fastapi import FastAPI

app = FastAPI(title="Employee Eval POC")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
