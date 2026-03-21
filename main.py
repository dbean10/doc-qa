import os
from fastapi import FastAPI
from google.cloud import secretmanager

app = FastAPI(title="Doc QA API")


def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "doc-qa-learn")
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/test-connections")
def test_connections():
    results = {}

    # Test Anthropic
    try:
        import anthropic
        key = get_secret("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        results["anthropic"] = {"status": "ok", "response": msg.content[0].text}
    except Exception as e:
        results["anthropic"] = {"status": "error", "error": str(e)}

    # Test OpenAI
    try:
        import openai
        key = get_secret("OPENAI_API_KEY")
        client = openai.OpenAI(api_key=key)
        resp = client.embeddings.create(
            model="text-embedding-3-large",
            input="test",
        )
        results["openai"] = {"status": "ok", "dimensions": len(resp.data[0].embedding)}
    except Exception as e:
        results["openai"] = {"status": "error", "error": str(e)}

    return results
