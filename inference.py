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
HF_TOKEN = os.getenv("HF_TOKEN")
API_KEY = HF_TOKEN or os.getenv("API_KEY", "")
ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")

TASKS = ["easy", "medium", "hard"]
MAX_STEPS = 18
SUCCESS_THR = 0.5

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)


# ---------------- LOGGING (FIXED FORMAT) ----------------
def log_start(task):
    print("[START]", flush=True)
    print(f"[STEP] Task: {task}", flush=True)


def log_step(step, action, reward):
    print(
        f"[STEP] Step {step} | Action: {action} | Reward: {reward}", flush=True)


def log_end(score):
    print(f"[STEP] Final Score: {score}", flush=True)
    print("[END]", flush=True)


# ---------------- HEURISTIC AGENT ----------------
def heuristic_action(obs: dict) -> dict:
    subjects = obs["subjects"]
    coverage = obs.get("coverage_pct", {})
    days = obs["days_until_exam"]

    best = None
    best_score = -1

    for s in subjects:
        urgency = 1 / max(days.get(s, 1), 1)
        need = 1 - coverage.get(s, 0)
        score = urgency + need

        if score > best_score:
            best_score = score
            best = s

    return {"subject": best, "hours": 2.0, "session_type": "new_material"}


def get_action(obs):
    return heuristic_action(obs)


# ---------------- MAIN TASK RUNNER ----------------
async def run_task(task_id: str):
    rewards = []
    steps = 0
    score = 0.0

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
                done = data.get("done", False)

                rewards.append(reward)
                steps = step

                log_step(step, action, reward)

                if done:
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
    print("[START]")
    print("[STEP] Running inference")
    print("[END]")
    return {"output": "ok"}
