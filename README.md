---
title: CodeReview
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
tags:
  - openenv
---

# 🔍 Code Review Environment — OpenEnv

An AI agent environment for automated code review. The agent reviews Python
code snippets, identifies bugs by line number, classifies severity, and
suggests fixes — just like a human code reviewer.

## Why Code Review?

Code review is the #1 most common developer workflow. Every pull request at
every company goes through it. Training AI agents to do it well has
**immediate, massive real-world value**:

- **$100B+ industry**: automated code review tools (SonarQube, CodeClimate,
  GitHub Copilot code review) are a huge market.
- **Clear success criteria**: bugs are either there or not — grading is
  deterministic.
- **Progressive difficulty**: from catching typos to finding SQL injection
  vulnerabilities.

## Environment Overview

| Property | Value |
|---|---|
| **Domain** | Code Review (Python) |
| **Action space** | `message: str` — the agent's review text |
| **Observation space** | Code snippet + task info + grader feedback |
| **Reward range** | 0.0–1.0 (normalized per-task) |
| **Tasks** | 3 (easy → medium → hard) |
| **Grading** | Deterministic keyword + line-number matching |

### Action Space

The agent sends a single string message containing its code review findings:

```python
CodeReviewAction(message="Line 23: integer division (//) truncates the average...")
```

### Observation Space

| Field | Type | Description |
|---|---|---|
| `code_snippet` | `str` | The Python code to review |
| `task_name` | `str` | Task identifier |
| `task_description` | `str` | What the agent should do |
| `language` | `str` | Always "python" |
| `filename` | `str` | Simulated filename |
| `feedback` | `str` | Grader feedback on last action |
| `bugs_found` | `int` | Correctly identified bugs so far |
| `total_bugs` | `int` | Total bugs in the code |
| `current_score` | `float` | Running score (0.0–1.0) |
| `step_number` | `int` | Current step |
| `max_steps` | `int` | Maximum steps for this task |
| `echoed_message` | `str` | Echo of agent's last message |

## Tasks

### 1. `single_bug` (Easy)

**Code**: A student grade processing function (~30 lines)  
**Bugs**: 2 (integer division, off-by-one index)  
**Max steps**: 5  
**Expected score**: 0.5–0.9 for capable models  

A good warm-up — both bugs are common Python mistakes that any experienced
developer would catch.

### 2. `multi_bug` (Medium)

**Code**: A CSV employee data processor (~55 lines)  
**Bugs**: 4 (resource leak, impossible condition, missing close, validation gap)  
**Max steps**: 8  
**Expected score**: 0.3–0.7 for capable models  

Requires understanding of resource management, boolean logic, and data
validation patterns.

### 3. `full_review` (Hard)

**Code**: A TaskManager class with SQLite (~90 lines)  
**Bugs**: 6 (2× SQL injection, silent failure, null crash, missing error
handling, unreliable cleanup)  
**Max steps**: 10  
**Expected score**: 0.2–0.5 for capable models  

Demands security awareness, error handling knowledge, and Python best
practices. The SQL injection bugs require understanding of parameterized
queries.

## Reward Design

Rewards are earned **per step** (not just end-of-episode), providing useful
gradient signal:

- **Line number match** (±3 lines): 40% of each bug's points
- **Bug-type keywords detected**: 40% of each bug's points
- **Fix suggestion keywords**: 20% of each bug's points
- **Partial credit**: if keywords match but line number is wrong, 25% credit

Bug point values scale with severity:
- Critical: 3.0 points
- Major: 2.0 points
- Minor: 1.0 points

Final score = earned points / max possible points, clamped to [0, 1].

## Setup & Usage

### Prerequisites

- Python 3.10+
- Docker (for containerized deployment)

### Local Development

```bash
# Clone and install
git clone <repo-url>
cd OpenEnv
pip install -e .

# Start the server
uvicorn code_review_env.server.app:app --host 0.0.0.0 --port 7860

# In another terminal, run inference
export HF_TOKEN="your-api-key"
python inference.py
```

### Docker

```bash
# Build
docker build -t code-review-env .

# Run
docker run -p 7860:7860 code-review-env

# Test
curl -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{}'
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `HF_TOKEN` | Hugging Face API key | — |
| `API_BASE_URL` | LLM API endpoint | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model to use | `Qwen/Qwen2.5-72B-Instruct` |
| `ENV_BASE_URL` | Environment server URL | `http://localhost:7860` |

## API Reference

### `POST /reset`

Reset the environment and load a task.

```json
{"task": "single_bug"}
```

Returns: `{observation, reward, done, info}`

### `POST /step`

Submit a review message.

```json
{"message": "Line 23 has an integer division bug..."}
```

Returns: `{observation, reward, done, info}`

### `GET /state`

Get current episode state.

Returns: `{episode_id, step_count, task_name, score, bugs_identified, done}`

## Baseline Scores

Scores from `Qwen/Qwen2.5-72B-Instruct`:

| Task | Score | Steps |
|---|---|---|
| `single_bug` | ~0.70 | 3 |
| `multi_bug` | ~0.45 | 6 |
| `full_review` | ~0.30 | 8 |

## Project Structure

```
├── code_review_env/
│   ├── __init__.py           # Package exports
│   ├── models.py             # Pydantic models (Action, Observation, State)
│   ├── client.py             # Async HTTP client
│   └── server/
│       ├── app.py            # FastAPI application
│       ├── code_review_environment.py  # Environment logic
│       ├── grader.py         # Deterministic grading engine
│       └── tasks.py          # Task definitions & bug database
├── openenv.yaml              # OpenEnv manifest
├── pyproject.toml            # Package configuration
├── requirements.txt          # Pip dependencies
├── Dockerfile                # Container definition
├── inference.py              # Baseline inference script
└── README.md                 # This file
```

## License

MIT
