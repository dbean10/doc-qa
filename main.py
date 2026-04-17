# main.py — updated
from fastapi import FastAPI
from lab7.tools_api import router as tools_router

app = FastAPI(title="Doc QA API")

app.include_router(tools_router)

@app.get("/health")
def health():
    return {"status": "ok"}