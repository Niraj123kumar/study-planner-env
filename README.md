---
title: Study Planner Env
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8000
tags:
  - openenv
---

# Study Planner OpenEnv

[![HF Space](https://img.shields.io/badge/🤗-Open%20in%20Spaces-blue)](https://huggingface.co/spaces/ride4code/study-planner-env) [![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-green)](https://huggingface.co/spaces/ride4code/study-planner-env)

## Demo

### Live HF Space
The environment is deployed and responding at https://ride4code-study-planner-env.hf.space

![HF Space health endpoint returning status healthy](docs/hf-space.png)

### Agent Run
Below is a real agent run showing the structured `[START]` `[STEP]` `[END]` log format required by the OpenEnv spec. The smart agent prioritises subjects by urgency, coverage gap, and fatigue level.

![Agent run showing START STEP END logs across easy medium and hard tasks](docs/agent-run.png)

## Why This Environment Exists

Study planning is one of the most universal human tasks, yet no existing OpenEnv environment models it. Unlike game-based benchmarks, this environment captures real cognitive constraints: knowledge decays without review, fatigue accumulates with repeated study, subject dependencies enforce learning order, and unexpected disruptions force dynamic replanning. An agent that performs well here has learned genuine scheduling intelligence — not just pattern matching. This fills a direct gap in the RL benchmark ecosystem.

An RL environment where AI agents allocate study hours across subjects to maximise exam coverage under time and budget constraints. Features fatigue modeling, retention decay, subject dependencies, mock exams, and exam surprises.

## Action Space
```json
{"subject": "Math", "hours": 2.0, "session_type": "new_material"}
```
- `subject`: one of the available subjects for the task
- `hours`: float between 0.0 and 12.0
- `session_type`: `new_material` | `review` | `practice` (practice requires 50% coverage first)

## Observation Space
```json
{
  "subjects": ["Math", "Physics", "Chemistry"],
  "hours_remaining": {"Math": 4.0, "Physics": 4.0, "Chemistry": 3.0},
  "days_until_exam": {"Math": 5, "Physics": 7, "Chemistry": 6},
  "total_hours_left": 16.0,
  "coverage_pct": {"Math": 0.6, "Physics": 0.4, "Chemistry": 0.3},
  "retention": {"Math": 0.6, "Physics": 0.4, "Chemistry": 0.3},
  "fatigue_level": {"Math": 0.5, "Physics": 0.0, "Chemistry": 0.0},
  "study_history": {"Math": [2.0, 2.0], "Physics": [], "Chemistry": []},
  "session_count": {"Math": 2, "Physics": 0, "Chemistry": 0},
  "dependency_unlocked": {"Math": true, "Physics": false, "Chemistry": true},
  "available_session_types": {"Math": ["new_material", "review", "practice"]},
  "mock_exam_result": null,
  "exam_schedule_changed": false,
  "message": "Allocated 2.0h to Math.",
  "done": false
}
```

## Tasks

| Task | Subjects | Budget | Required | Difficulty | Max Score |
|------|----------|--------|----------|------------|-----------|
| easy | 3 | 18h | 13h | No penalties, no decay | 1.00 |
| medium | 4 | 22h | 25h | Disruptions, 4% decay, mock exam | ~0.75 |
| hard | 5 | 26h | 35h | Dependencies, surprise, 7% decay | ~0.45 |
| extreme | 6 | 24h | 55h | All mechanics, 10% decay, 6 disruptions | ~0.25 |

## Baseline Scores

| Task | Random Agent | Smart Agent (Qwen2.5-72B) | Gap |
|------|-------------|--------------------------|-----|
| easy | 0.87 | 1.00 | +0.13 |
| medium | 0.21 | 0.54 | +0.33 |
| hard | 0.15 | 0.21 | +0.06 |
| extreme | ~0.05 | ~0.07 | +0.02 |

The gap on medium (+0.33) demonstrates the reward signal is meaningful — a smart agent significantly outperforms random allocation.

## Key Mechanics

- **Fatigue**: Repeated study of same subject reduces effective hours
- **Retention Decay**: Knowledge fades if subject not reviewed — agent must re-study
- **Dependencies**: Some subjects require prerequisite coverage first
- **Mock Exam**: Mid-episode exam reveals weak subjects and boosts their priority
- **Exam Surprise**: One subject exam moves 2 days earlier unexpectedly
- **Session Types**: new_material, review, practice — each with different fatigue/retention tradeoffs

## Setup
```bash
uv sync
uv run uvicorn server.app:app --port 8000
```

## Docker
```bash
docker build -t study-planner-env .
docker run -p 8000:8000 study-planner-env
```

## Inference
```bash
export HF_TOKEN=your_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export ENV_URL=http://localhost:8000
python3 inference.py
```

## Web UI

An interactive dashboard is available at `/web` — try it live at https://ride4code-study-planner-env.hf.space/web

## API Endpoints

- `GET /health` — health check
- `POST /reset?task_id=easy` — reset environment (easy/medium/hard/extreme)
- `POST /step` — `{"subject": "Math", "hours": 2.0, "session_type": "new_material"}`
- `GET /grade` — final score (0.0-1.0)
- `GET /state` — current state
- `GET /web` — web UI
