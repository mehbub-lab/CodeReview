"""
Inference Script — Code Review Environment
===========================================

MANDATORY STDOUT FORMAT:
  [START] task=<task_name> env=code_review_env model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

Runs all 3 tasks (single_bug, multi_bug, full_review) sequentially.
Uses the OpenAI client for LLM calls.
"""

import asyncio
import os
import sys
import textwrap
from typing import List, Optional

from openai import OpenAI

# ── client import ─────────────────────────────────────────────────────────
from code_review_env.client import CodeReviewEnv
from code_review_env.models import CodeReviewAction

# ── configuration ─────────────────────────────────────────────────────────
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
ENV_BASE_URL = os.getenv("ENV_BASE_URL") or "http://localhost:7860"
BENCHMARK = "code_review_env"

# Per-task config
TASK_CONFIG = {
    "single_bug": {"max_steps": 5, "threshold": 0.3},
    "multi_bug": {"max_steps": 8, "threshold": 0.2},
    "full_review": {"max_steps": 10, "threshold": 0.15},
}

TEMPERATURE = 0.4
MAX_TOKENS = 1024


# ── logging helpers ───────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]):
    action_clean = action.replace("\n", " ")[:200]
    done_str = "true" if done else "false"
    error_str = error if error else "null"
    print(
        f"[STEP] step={step} action={action_clean} reward={reward:.2f} "
        f"done={done_str} error={error_str}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    success_str = "true" if success else "false"
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={success_str} steps={steps} score={score:.2f} "
        f"rewards={rewards_str}",
        flush=True,
    )


# ── LLM interaction ──────────────────────────────────────────────────────

def build_system_prompt(task_name: str) -> str:
    return textwrap.dedent(f"""\
        You are an expert code reviewer. You are reviewing Python code for bugs.

        TASK: {task_name}

        Your job:
        1. Carefully read the code provided in the observation
        2. Identify bugs — for each bug state:
           - The exact LINE NUMBER (e.g., "line 23")
           - The bug type (e.g., "logic error", "security vulnerability")
           - A clear description of what's wrong
           - A suggested fix
        3. Focus on finding bugs you haven't mentioned before
        4. Be specific about line numbers — this is critical for scoring

        Reply with your review findings. Be thorough and precise.
    """)


def get_model_message(
    client: OpenAI,
    step: int,
    code_snippet: str,
    feedback: str,
    bugs_found: int,
    total_bugs: int,
    history: List[str],
    task_name: str,
) -> str:
    """Call the LLM to get the next review message."""
    messages = [{"role": "system", "content": build_system_prompt(task_name)}]

    # First step: show the code
    if step == 1:
        messages.append({
            "role": "user",
            "content": (
                f"Please review this Python code and find {total_bugs} bugs:\n\n"
                f"```python\n{code_snippet}\n```\n\n"
                "Identify each bug with its line number, description, and fix."
            ),
        })
    else:
        # Follow-up steps: give feedback and ask for more
        messages.append({
            "role": "user",
            "content": (
                f"Code to review:\n```python\n{code_snippet}\n```\n\n"
                f"Previous feedback: {feedback}\n"
                f"Bugs found so far: {bugs_found}/{total_bugs}\n\n"
                f"Previous findings:\n" + "\n".join(history[-3:]) + "\n\n"
                f"Find the remaining {total_bugs - bugs_found} bug(s) you haven't found yet. "
                "Focus on different line numbers and bug types."
            ),
        })

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error calling LLM: {e}"


# ── main loop ─────────────────────────────────────────────────────────────

async def run_task(task_name: str, env: CodeReviewEnv, llm: OpenAI):
    """Run a single task and return the score."""
    config = TASK_CONFIG[task_name]
    max_steps = config["max_steps"]
    threshold = config["threshold"]

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(task=task_name)
        obs = result.observation
        code_snippet = obs.code_snippet
        total_bugs = obs.total_bugs
        history: List[str] = []

        for step in range(1, max_steps + 1):
            if result.done:
                break

            message = get_model_message(
                client=llm,
                step=step,
                code_snippet=code_snippet,
                feedback=obs.feedback,
                bugs_found=obs.bugs_found,
                total_bugs=total_bugs,
                history=history,
                task_name=task_name,
            )

            result = await env.step(CodeReviewAction(message=message))
            obs = result.observation
            reward = result.reward or 0.0
            done = result.done
            error = None

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=message, reward=reward, done=done, error=error)

            history.append(f"Step {step}: Found {obs.bugs_found}/{total_bugs} bugs (reward {reward:+.2f})")

            if done:
                break

        score = sum(rewards)
        score = min(max(score, 0.0), 1.0)
        success = score >= threshold

    except Exception as e:
        print(f"[DEBUG] Error during task {task_name}: {e}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main():
    if not API_KEY:
        print("[ERROR] No API key found. Set HF_TOKEN, API_KEY, or OPENAI_API_KEY.", flush=True)
        sys.exit(1)

    llm = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

    tasks = ["single_bug", "multi_bug", "full_review"]
    scores = {}

    for task_name in tasks:
        async with CodeReviewEnv(base_url=ENV_BASE_URL) as env:
            score = await run_task(task_name, env, llm)
            scores[task_name] = score

    print("\n" + "=" * 50, flush=True)
    print("FINAL SCORES", flush=True)
    print("=" * 50, flush=True)
    for task, sc in scores.items():
        print(f"  {task}: {sc:.2f}", flush=True)
    avg = sum(scores.values()) / len(scores) if scores else 0.0
    print(f"  AVERAGE: {avg:.2f}", flush=True)
    print("=" * 50, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
