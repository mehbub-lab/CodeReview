"""
Typed Pydantic models for the Code Review Environment.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class CodeReviewAction(BaseModel):
    """Action: the agent sends a review message identifying bugs and fixes."""

    message: str = Field(
        ...,
        description="The agent's code review message. Should identify bugs by line number, "
        "describe the issue, and optionally suggest a fix.",
    )


class CodeReviewObservation(BaseModel):
    """Observation: what the agent sees after each step."""

    code_snippet: str = Field(
        default="", description="The Python code snippet to review"
    )
    task_name: str = Field(default="", description="Current task identifier")
    task_description: str = Field(
        default="", description="Human-readable task instructions"
    )
    language: str = Field(default="python", description="Programming language")
    filename: str = Field(default="", description="Simulated filename")
    feedback: str = Field(
        default="", description="Grader feedback on the last action"
    )
    bugs_found: int = Field(
        default=0, description="Number of bugs correctly identified so far"
    )
    total_bugs: int = Field(
        default=0, description="Total number of bugs in the code"
    )
    current_score: float = Field(
        default=0.0, description="Running score for this episode (0.0–1.0)"
    )
    step_number: int = Field(default=0, description="Current step number")
    max_steps: int = Field(
        default=5, description="Maximum steps allowed for this task"
    )
    echoed_message: str = Field(
        default="", description="Echo of the agent's last message"
    )


class CodeReviewState(BaseModel):
    """State: internal episode tracking."""

    episode_id: str = Field(default="", description="Unique episode identifier")
    step_count: int = Field(default=0, description="Steps taken so far")
    task_name: str = Field(default="", description="Current task")
    score: float = Field(default=0.0, description="Accumulated score")
    bugs_identified: List[str] = Field(
        default_factory=list, description="IDs of bugs found so far"
    )
    done: bool = Field(default=False, description="Whether the episode is over")
    max_score: float = Field(default=0.0, description="Maximum achievable score")
