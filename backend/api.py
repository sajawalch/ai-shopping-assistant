"""FastAPI backend.

Local:       uvicorn api:app --reload --port 8000
Production:  uvicorn api:app --host 0.0.0.0 --port $PORT     (single worker)

Environment variables:
  OPENAI_API_KEY     required
  SHOPPING_MODEL     optional, default gpt-4o
  ALLOWED_ORIGINS    comma-separated frontend addresses, e.g. https://sahipick.vercel.app
  TAVILY_API_KEY     recommended: reliable store search (free key at tavily.com)
  RATE_LIMIT_PER_HOUR  optional, requests per visitor per hour (default 60)
"""
import os
import time
import uuid
from collections import OrderedDict, defaultdict

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env if present

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from langgraph.types import Command  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from graph import build_graph  # noqa: E402
from payload import to_payload  # noqa: E402
from tools import search_provider  # noqa: E402

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
origins += [o.strip().rstrip("/") for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app = FastAPI(title="Sahi Pick API")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

graph = build_graph()  # one compiled graph; each chat is its own thread_id
MAX_SESSIONS = 1000
sessions: "OrderedDict[str, float]" = OrderedDict()

# Simple per-visitor rate limit so a public site cannot run up your OpenAI bill.
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_HOUR", "60"))
_hits: dict[str, list[float]] = defaultdict(list)


def check_rate(request: Request) -> None:
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    now = time.time()
    recent = [t for t in _hits[ip] if now - t < 3600]
    if len(recent) >= RATE_LIMIT:
        raise HTTPException(429, "Too many requests. Please wait a while and try again.")
    recent.append(now)
    _hits[ip] = recent


class Reply(BaseModel):
    answer: str


@app.get("/")
def root():
    return {"message": "Sahi Pick API is running."}


@app.get("/api/health")
def health():
    return {"status": "ok", "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
            "search_provider": search_provider()}


@app.post("/api/sessions")
def start_session(request: Request):
    """Start a new chat; returns the first question."""
    check_rate(request)
    thread_id = str(uuid.uuid4())
    sessions[thread_id] = time.time()
    while len(sessions) > MAX_SESSIONS:
        sessions.popitem(last=False)
    try:
        result = graph.invoke({}, {"configurable": {"thread_id": thread_id}})
    except Exception as exc:
        raise HTTPException(500, f"{type(exc).__name__}: {exc}")
    return to_payload(thread_id, result)


@app.post("/api/sessions/{thread_id}/reply")
def reply(thread_id: str, body: Reply, request: Request):
    """Send the user's answer; returns the next question, recommendation or done."""
    check_rate(request)
    if thread_id not in sessions:
        raise HTTPException(404, "Unknown session. Start a new search.")
    try:
        result = graph.invoke(Command(resume=body.answer),
                              {"configurable": {"thread_id": thread_id}})
    except Exception as exc:
        raise HTTPException(500, f"{type(exc).__name__}: {exc}")
    return to_payload(thread_id, result)
