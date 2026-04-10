"""
inference.py — Study Planner OpenEnv Baseline Inference Script
"""

import asyncio
import json
import os
import httpx
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN", "")
ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")

TASKS = ["easy", "medium", "hard"]
MAX_STEPS = 18

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

# ---------------- LOGGING (FIXED FORMAT) ----------------

def log_start(task):
    print("[START]", flush=True)
    print(f"[STEP] Task: {task}", flush=True)

def log_step(step, action, reward):
    print(f"[STEP] Step {step} | Action: {action} | Reward: {reward}", flush=True)

def log_end(score):
    print(f"[STEP] Final Score: {score}", flush=True)
    print("[END]", flush=True)

# ---------------- LLM AGENT ----------------

def get_action(obs: dict) -> dict:
    prompt = f"""You are a study planning agent. Given this observation:
{json.dumps(obs, indent=2)}

Pick the best next study action. Consider urgency (days until exam), coverage gaps, fatigue, and dependencies.
Respond ONLY with a valid JSON object, no explanation:
{{"subject": "<subject>", "hours": <float 0.5-4.0>, "session_type": "<new_material|review|practice>"}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        text = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"[STEP] LLM error, falling back to heuristic: {e}", flush=True)
        # Fallback heuristic
        subjects = obs["subjects"]
        coverage = obs.get("coverage_pct", {})
        days = obs["days_until_exam"]
        best, best_score = None, -1
        for s in subjects:
            score = (1 / max(days.get(s, 1), 1)) + (1 - coverage.get(s, 0))
            if score > best_score:
                best_score, best = score, s
        return {"subject": best, "hours": 2.0, "session_type": "new_material"}

# ---------------- MAIN TASK RUNNER ----------------

async def run_task(task_id: str):
    log_start(task_id)
    async with httpx.AsyncClient(timeout=60) as http:
        try:
            r = await http.post(f"{ENV_URL}/reset?task_id={task_id}")
            obs = r.json()["observation"]

            for step in range(1, MAX_STEPS + 1):
                if obs.get("done"):
                    break
                action = get_action(obs)
                r = await http.post(f"{ENV_URL}/step", json=action)
                data = r.json()
                obs = data["observation"]
                reward = data.get("reward", 0.0)
                log_step(step, action, reward)
                if data.get("done"):
                    break

            r = await http.get(f"{ENV_URL}/grade")
            score = r.json().get("score", 0.0)
        except Exception as e:
            print(f"[STEP] Error: {e}", flush=True)
            score = 0.0

    log_end(score)

# ---------------- ENTRY POINT ----------------

async def main():
    for task in TASKS:
        await run_task(task)

if __name__ == "__main__":
    asyncio.run(main())

# ---------------- REQUIRED RUN FUNCTION ----------------

def run(input_data):
    asyncio.run(main())
    return {"output": "ok"}
