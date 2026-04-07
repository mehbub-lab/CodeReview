"""
Lightweight async client for the Code Review Environment.

Wraps HTTP calls so the inference script can use a clean API.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from code_review_env.models import (
    CodeReviewAction,
    CodeReviewObservation,
)


@dataclass
class StepResult:
    """Result returned by env.step() / env.reset()."""

    observation: CodeReviewObservation
    reward: float = 0.0
    done: bool = False
    info: Dict[str, Any] = field(default_factory=dict)


class CodeReviewEnv:
    """Async HTTP client for the Code Review Environment."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("ENV_BASE_URL", "http://localhost:7860")).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "CodeReviewEnv":
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
        return self._client

    async def reset(self, task: str = "single_bug", **kwargs: Any) -> StepResult:
        client = self._ensure_client()
        body = {"task": task, **kwargs}
        resp = await client.post("/reset", json=body)
        resp.raise_for_status()
        data = resp.json()
        return self._parse(data)

    async def step(self, action: CodeReviewAction) -> StepResult:
        client = self._ensure_client()
        resp = await client.post("/step", json=action.model_dump())
        resp.raise_for_status()
        data = resp.json()
        return self._parse(data)

    async def state(self) -> Dict[str, Any]:
        client = self._ensure_client()
        resp = await client.get("/state")
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse(data: Dict[str, Any]) -> StepResult:
        obs_data = data.get("observation", {})
        return StepResult(
            observation=CodeReviewObservation(**obs_data),
            reward=data.get("reward", 0.0),
            done=data.get("done", False),
            info=data.get("info", {}),
        )
