"""
Code Review Environment — server-side implementation.

Implements the OpenEnv Environment interface:
  reset()  → initial observation
  step()   → observation, reward, done
  state()  → episode metadata
"""

from typing import Any, Optional, Set
from uuid import uuid4

from code_review_env.models import (
    CodeReviewAction,
    CodeReviewObservation,
    CodeReviewState,
)
from code_review_env.server.tasks import get_task, list_tasks, Task
from code_review_env.server.grader import grade_message


class CodeReviewEnvironment:
    """
    An OpenEnv environment where an agent reviews Python code to find bugs.

    The agent receives a code snippet and must identify bugs by line number,
    describe the issue, and suggest fixes.  A deterministic grader scores
    each response using keyword & line-number matching.
    """

    def __init__(self):
        self._state = CodeReviewState()
        self._task: Optional[Task] = None
        self._found_bugs: Set[str] = set()
        self._total_reward: float = 0.0
        self._last_message: str = ""

    # ----- OpenEnv interface -----

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        """Reset the environment and load a task.

        Accepts ``task`` as a keyword argument (default ``"single_bug"``).
        """
        task_name = kwargs.get("task", "single_bug")
        self._task = get_task(task_name)
        self._found_bugs = set()
        self._total_reward = 0.0
        self._last_message = ""

        self._state = CodeReviewState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_name=task_name,
            score=0.0,
            bugs_identified=[],
            done=False,
            max_score=self._task.max_score,
        )

        obs = CodeReviewObservation(
            code_snippet=self._task.code,
            task_name=self._task.name,
            task_description=self._task.description,
            language=self._task.language,
            filename=self._task.filename,
            feedback="Environment reset. Review the code and find the bugs!",
            bugs_found=0,
            total_bugs=len(self._task.bugs),
            current_score=0.0,
            step_number=0,
            max_steps=self._task.max_steps,
            echoed_message="",
        )

        return {
            "observation": obs.model_dump(),
            "reward": 0.0,
            "done": False,
            "info": {"task": task_name, "available_tasks": list_tasks()},
        }

    def step(
        self,
        action: Any,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> dict:
        """Execute one review step."""
        if self._task is None:
            return self._error_response("Environment not reset. Call /reset first.")

        if self._state.done:
            return self._error_response("Episode already finished. Call /reset.")

        # Extract message from action
        if isinstance(action, CodeReviewAction):
            message = action.message
        elif isinstance(action, dict):
            message = action.get("message", "")
        else:
            message = str(action)

        self._last_message = message
        self._state.step_count += 1

        # Grade the message
        grade = grade_message(message, self._task.bugs, self._found_bugs)

        # Update state
        self._found_bugs.update(grade.new_bugs_found)
        self._state.bugs_identified = list(self._found_bugs)

        # Normalize reward to contribution toward [0, 1] total score
        step_reward = grade.step_reward / self._task.max_score if self._task.max_score > 0 else 0.0
        step_reward = min(step_reward, 1.0 - self._total_reward)  # clamp
        self._total_reward += step_reward
        self._state.score = round(self._total_reward, 4)

        # Check if done
        all_found = len(self._found_bugs) >= len(self._task.bugs)
        max_steps_hit = self._state.step_count >= self._task.max_steps
        self._state.done = all_found or max_steps_hit

        # Build final feedback
        feedback = grade.feedback
        if self._state.done:
            if all_found:
                feedback += " 🎉 All bugs found! Episode complete."
            else:
                remaining = len(self._task.bugs) - len(self._found_bugs)
                feedback += f" Episode ended. {remaining} bug(s) remain unfound."

        obs = CodeReviewObservation(
            code_snippet=self._task.code,
            task_name=self._task.name,
            task_description=self._task.description,
            language=self._task.language,
            filename=self._task.filename,
            feedback=feedback,
            bugs_found=len(self._found_bugs),
            total_bugs=len(self._task.bugs),
            current_score=round(self._total_reward, 4),
            step_number=self._state.step_count,
            max_steps=self._task.max_steps,
            echoed_message=message,
        )

        return {
            "observation": obs.model_dump(),
            "reward": round(step_reward, 4),
            "done": self._state.done,
            "info": {
                "bugs_found": list(self._found_bugs),
                "new_bugs_this_step": grade.new_bugs_found,
            },
        }

    @property
    def state(self) -> dict:
        """Return current episode state."""
        return self._state.model_dump()

    # ----- helpers -----

    def _error_response(self, msg: str) -> dict:
        obs = CodeReviewObservation(
            feedback=msg,
            echoed_message=self._last_message,
        )
        return {
            "observation": obs.model_dump(),
            "reward": 0.0,
            "done": True,
            "info": {"error": msg},
        }
