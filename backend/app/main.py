from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent import SAMPLE_QUESTIONS, get_audit, run_agent
from .config import CORS_ORIGINS, DEMO_RESET_ENABLED, ROOT_DIR, public_runtime_config
from .database import init_db
from .schema_catalog import get_schema_catalog

DIST_DIR = ROOT_DIR / "dist"
DIST_INDEX = DIST_DIR / "index.html"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="DB Sentinel Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


@app.get("/api/schema")
def schema() -> dict[str, Any]:
    catalog = get_schema_catalog()
    catalog["sample_questions"] = SAMPLE_QUESTIONS
    return catalog


@app.get("/api/config")
def config() -> dict[str, Any]:
    return public_runtime_config()


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    return run_agent(request.question.strip())


@app.get("/api/audit/{session_id}")
def audit(session_id: str) -> dict[str, Any]:
    records = get_audit(session_id)
    if not records:
        raise HTTPException(status_code=404, detail="audit session not found")
    return {"session_id": session_id, "records": records}


@app.post("/api/demo/reset")
def reset_demo() -> dict[str, str]:
    if not DEMO_RESET_ENABLED:
        raise HTTPException(status_code=403, detail="demo reset disabled")
    path = init_db(force=True)
    return {"status": "reset", "database": str(path)}


def _frontend_response(request_path: str) -> FileResponse:
    if not DIST_INDEX.is_file():
        raise HTTPException(
            status_code=404,
            detail="frontend build not found; run npm run build before single-service startup",
        )

    normalized_path = request_path.strip("/")
    if normalized_path:
        candidate = (DIST_DIR / normalized_path).resolve()
        try:
            candidate.relative_to(DIST_DIR.resolve())
        except ValueError:
            candidate = DIST_INDEX
        if candidate.is_file():
            return FileResponse(candidate)

    return FileResponse(DIST_INDEX)


@app.get("/", include_in_schema=False)
def frontend_root() -> FileResponse:
    return _frontend_response("")


@app.get("/{request_path:path}", include_in_schema=False)
def frontend_fallback(request_path: str) -> FileResponse:
    if request_path == "api" or request_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="api endpoint not found")
    return _frontend_response(request_path)
