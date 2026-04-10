"""
inference.py — Study Planner OpenEnv Baseline Inference Script
"""

import asyncio
import json
import os
import httpx
from openai import OpenAI

API_BASE_URL = os.environ["API_BASE_URL"]
API_KEY      = os.environ["API_KEY"]
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL      = os.getenv("ENV_URL", "http://localhost:8000")

TASKS     = ["easy", "medium", "hard"]
MAX_STEPS = 18

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

def log_start(task):
    print("[START]", flush=True)
    print(f"[STEP] Task: {task}", flush=True)

def log_step(step, action, reward):
    print(f"[STEP] Step {step} | Action: {action} | Reward: {reward}", flush=True)

def log_end(score):
    print(f"[STEP] Final Score: {score}", flush=True)
    print("[END]", flush=True)

def get_action(obs: dict) -> dict:
    prompt = f"""You are a smart study planner agent.

Current state:
{json.dumps(obs, indent=2)}

Choose the best next study action. Reply ONLY with valid JSON in this exact format:
{{"subject": "<subject name>", "hours": <float 0.5-4.0>, "session_type": "<new_material|review|practice>"}}

Rules:
- Only use subjects listed in obs["subjects"]
- Use "practice" only if coverage_pct for that subject >= 0.5
- Prioritize subjects with low coverage and exams soon
- Keep hours between 0.5 and 4.0"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        action = json.loads(raw)
        assert "subject" in action and "hours" in action and "session_type" in action
        return action
    except Exception as e:
        print(f"[STEP] LLM parse error ({e}), using fallback", flush=True)
        return _heuristic_fallback(obs)

def _heuristic_fallback(obs: dict) -> dict:
    subjects = obs["subjects"]
    coverage = obs.get("coverage_pct", {})
    days     = obs["days_until_exam"]
    best, best_score = None, -1
    for s in subjects:
        score = (1 / max(days.get(s, 1), 1)) + (1 - coverage.get(s, 0))
        if score > best_score:
            best_score, best = score, s
    return {"subject": best, "hours": 2.0, "session_type": "new_material"}

async def run_task(task_id: str):
    log_start(task_id)
    async with httpx.AsyncClient(timeout=60) as http:
        try:
            r   = await http.post(f"{ENV_URL}/reset?task_id={task_id}")
            obs = r.json()["observation"]
            for step in range(1, MAX_STEPS + 1):
                if obs.get("done"):
                    break
                action = get_action(obs)
                r      = await http.post(f"{ENV_URL}/step", json=action)
                data   = r.json()
                obs    = data["observation"]
                reward = data.get("reward", 0.0)
                log_step(step, action, reward)
                if data.get("done"):
                    break
            r     = await http.get(f"{ENV_URL}/grade")
            score = r.json().get("score", 0.0)
        except Exception as e:
            print(f"[STEP] Error: {e}", flush=True)
            score = 0.0
    log_end(score)

async def main():
    for task in TASKS:
        await run_task(task)

if __name__ == "__main__":
    asyncio.run(main())

def run(input_data):
    print("[START]")
    print("[STEP] Running inference")
    asyncio.run(main())
    print("[END]")
    return {"output": "ok"}
