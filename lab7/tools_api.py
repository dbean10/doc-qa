# lab7/tools_api.py
"""
HTTP endpoints exposing the Week 4 tool implementations to the Next.js agent.

Mounted at /tools in main.py.
Each endpoint maps to one tool implementation — no business logic here,
just HTTP transport + Pydantic validation.

Morgan: Pydantic models are the validation layer at the HTTP boundary.
Same never-raises contract — errors returned as JSON, never as exceptions
that would surface as 500s to the agent loop.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
import sys
from pathlib import Path

# Make lab4 importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from lab4.tools.weather import get_weather
from lab4.tools.reminder import create_reminder
from lab4.rag.retriever import search_docs

router = APIRouter(prefix="/tools", tags=["tools"])


# ---------------------------------------------------------------------------
# Request models — Pydantic validates before tool functions are called.
# Morgan: type + length bounds at the HTTP boundary, Morgan's four checks
# inside the tool function. Two validation layers, same as MCP path.
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)

class WeatherRequest(BaseModel):
    location: str = Field(..., min_length=1, max_length=200)

class ReminderRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    time: str = Field(..., min_length=1, max_length=100)


# ---------------------------------------------------------------------------
# Endpoints — one per tool, POST only, JSON in/out.
# Never raises — tool implementations already return error dicts on failure.
# ---------------------------------------------------------------------------

@router.post("/search_docs")
def search_documents(req: SearchRequest) -> dict:
    """Search the document knowledge base via semantic similarity."""
    return search_docs(query=req.query)


@router.post("/get_weather")
def get_current_weather(req: WeatherRequest) -> dict:
    """Get current weather conditions for a location."""
    return get_weather(location=req.location)


@router.post("/create_reminder")
def create_reminder_endpoint(req: ReminderRequest) -> dict:
    """Save a reminder with text and time."""
    return create_reminder(text=req.text, time=req.time)