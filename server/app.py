"""
FastAPI application for the Code Review Environment.

Exposes the OpenEnv HTTP API:
  POST /reset   → initial observation
  POST /step    → step result (observation, reward, done)
  GET  /state   → episode metadata
"""

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from code_review_env.models import CodeReviewAction
from code_review_env.server.code_review_environment import CodeReviewEnvironment
from code_review_env.server.tasks import list_tasks

# ---------------------------------------------------------------------------
# Per-session environments
# ---------------------------------------------------------------------------
_envs: Dict[str, CodeReviewEnvironment] = {}
_default_env = CodeReviewEnvironment()


def _get_env(session_id: Optional[str] = None) -> CodeReviewEnvironment:
    if session_id and session_id in _envs:
        return _envs[session_id]
    return _default_env


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Code Review Environment",
    description="An OpenEnv environment for AI-powered code review training.",
    version="1.0.0",
)


class ResetRequest(BaseModel):
    task: str = "single_bug"
    seed: Optional[int] = None
    episode_id: Optional[str] = None
    session_id: Optional[str] = None


class StepRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    return {
        "name": "code_review_env",
        "version": "1.0.0",
        "description": "Code Review Environment for OpenEnv",
        "available_tasks": list_tasks(),
        "endpoints": ["/reset", "/step", "/state"],
    }


@app.post("/reset")
async def reset(body: ResetRequest = ResetRequest()):
    env = _get_env(body.session_id)
    if body.session_id:
        _envs[body.session_id] = env

    result = env.reset(
        seed=body.seed,
        episode_id=body.episode_id,
        task=body.task,
    )
    return JSONResponse(content=result)


@app.post("/step")
async def step(body: StepRequest):
    env = _get_env(body.session_id)
    action = CodeReviewAction(message=body.message)
    result = env.step(action)
    return JSONResponse(content=result)


@app.get("/state")
async def state(session_id: Optional[str] = None):
    env = _get_env(session_id)
    return JSONResponse(content=env.state)


@app.get("/tasks")
async def tasks():
    return {"tasks": list_tasks()}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    import uvicorn

    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
