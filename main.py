from fastapi import FastAPI

app = FastAPI(title="Doc QA API")

@app.get("/health")
def health():
    return {"status": "ok"}