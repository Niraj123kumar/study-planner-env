"""
inference.py — Study Planner OpenEnv Baseline Inference Script
Smart agent that prioritises by urgency, coverage gap, and fatigue.
Emits strictly formatted [START] [STEP] [END] logs per OpenEnv spec.
"""
import asyncio
import json
import os
import httpx
from openai import OpenAI
from typing import List, Optional

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
ENV_URL      = os.getenv("ENV_URL",      "http://localhost:8000")
BENCHMARK    = "study-planner-env"
TASKS        = ["easy", "medium", "hard"]
MAX_STEPS    = 18
SUCCESS_THR  = 0.5

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)


def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    print(f"[STEP] step={step} action={json.dumps(action)} reward={reward:.2f} done={str(done).lower()} error={error or 'null'}", flush=True)

def log_end(success, steps, score, rewards):
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={','.join(f'{r:.2f}' for r in rewards)}", flush=True)


def build_prompt(obs: dict) -> str:
    subjects       = obs["subjects"]
    hours_rem      = obs["hours_remaining"]
    days           = obs["days_until_exam"]
    budget         = obs["total_hours_left"]
    coverage       = obs.get("coverage_pct", {})
    fatigue        = obs.get("fatigue_level", {})
    history        = obs.get("study_history", {})
    dep_unlocked   = obs.get("dependency_unlocked", {})
    mock_result    = obs.get("mock_exam_result")
    surprise       = obs.get("exam_schedule_changed", False)
    message        = obs.get("message", "")

    lines = [
        f"You are a smart study planning agent. Budget left: {budget:.1f}h.",
        f"Message: {message}",
        "",
        "Current status per subject:",
    ]
    for s in subjects:
        locked = "" if dep_unlocked.get(s, True) else " [LOCKED - study dependency first]"
        fat = fatigue.get(s, 0.0)
        fat_warn = " [HIGH FATIGUE - avoid]" if fat > 0.5 else ""
        lines.append(
            f"  {s}: coverage={coverage.get(s,0):.0%}, hours_needed={hours_rem.get(s,0):.1f}h, "
            f"exam_in={days.get(s,0)}days, fatigue={fat:.0%}{locked}{fat_warn}"
        )

    if mock_result:
        lines.append("\nMOCK EXAM RESULTS (weak subjects have boosted priority):")
        for s, sc in mock_result.items():
            lines.append(f"  {s}: {sc:.0%}")

    if surprise:
        lines.append("\nWARNING: An exam was moved earlier! Re-evaluate priorities.")

    lines += [
        "",
        "Strategy rules:",
        "1. Never study a LOCKED subject until its dependency has 20%+ coverage.",
        "2. Avoid HIGH FATIGUE subjects — pick a different subject to recover.",
        "3. Prioritise subjects with closest exam AND lowest coverage.",
        "4. Never over-study penalty subjects (History, Chemistry in hard task).",
        "5. If mock exam showed weakness, focus on that subject now.",
        "",
        "Reply with ONLY valid JSON, no explanation:",
        '{"subject": "<subject_name>", "hours": <float 0.5-4.0>}',
    ]
    return "\n".join(lines)


def heuristic_action(obs: dict) -> dict:
    """Pure heuristic — always reliable, used as primary strategy."""
    subjects = obs["subjects"]
    days = obs["days_until_exam"]
    coverage = obs.get("coverage_pct", {s: 0.0 for s in subjects})
    fatigue = obs.get("fatigue_level", {s: 0.0 for s in subjects})
    dep_unlocked = obs.get("dependency_unlocked", {s: True for s in subjects})
    available = obs.get("available_session_types", {s: ["new_material"] for s in subjects})
    mock = obs.get("mock_exam_result") or {}
    hrs_rem = obs.get("hours_remaining", {s: 1.0 for s in subjects})

    best = None
    best_score = -1
    for s in subjects:
        # Skip locked subjects
        if not dep_unlocked.get(s, True):
            continue
        # Skip high fatigue
        if fatigue.get(s, 0.0) > 0.6:
            continue
        # Skip completed subjects
        if hrs_rem.get(s, 0.0) <= 0:
            continue
        urgency = 1.0 / max(days.get(s, 1), 1)
        need = 1.0 - coverage.get(s, 0.0)
        mock_bonus = 0.3 if mock.get(s, 1.0) < 0.5 else 0.0
        score = (urgency * 2.0 + need * 2.5 + mock_bonus)
        if score > best_score:
            best_score = score
            best = s

    # If all locked/fatigued, pick least fatigued unlocked
    if best is None:
        for s in subjects:
            if dep_unlocked.get(s, True):
                if best is None or fatigue.get(s, 0) < fatigue.get(best, 0):
                    best = s
    if best is None:
        best = subjects[0]

    # Pick best session type
    sess_types = available.get(best, ["new_material"])
    if "practice" in sess_types and coverage.get(best, 0) >= 0.7:
        session_type = "practice"
    elif fatigue.get(best, 0) > 0.3 and "review" in sess_types:
        session_type = "review"
    else:
        session_type = "new_material"

    return {"subject": best, "hours": 2.0, "session_type": session_type}


def get_action(obs: dict) -> dict:
    """Use LLM with heuristic fallback."""
    # Always compute heuristic first as safety net
    heuristic = heuristic_action(obs)
    prompt = build_prompt(obs)
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=60,
        )
        text = resp.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        action = json.loads(text)
        s = action["subject"]
        dep_unlocked = obs.get("dependency_unlocked", {})
        hrs_rem = obs.get("hours_remaining", {})
        # Validate LLM output — reject if clearly wrong
        if s not in obs["subjects"]:
            return heuristic
        if not dep_unlocked.get(s, True):
            return heuristic
        if hrs_rem.get(s, 1.0) <= 0:
            return heuristic
        action["hours"] = max(0.5, min(float(action["hours"]), 2.0))
        if action.get("session_type") not in ["new_material", "review", "practice"]:
            action["session_type"] = "new_material"
        return action
    except Exception:
        return heuristic


async def run_task(task_id: str):
    rewards = []
    steps = 0
    score = 0.0

    log_start(task_id, BENCHMARK, MODEL_NAME)

    async with httpx.AsyncClient(timeout=60) as http:
        try:
            r = await http.post(f"{ENV_URL}/reset?task_id={task_id}")
            obs = r.json()["observation"]

            for step in range(1, MAX_STEPS + 1):
                if obs.get("done", False):
                    break

                action = get_action(obs)
                r = await http.post(f"{ENV_URL}/step", json=action)
                data = r.json()
                obs = data["observation"]
                reward = data.get("reward", 0.0)
                done = data.get("done", False)

                rewards.append(reward)
                steps = step
                log_step(step, action, reward, done, None)

                if done:
                    break

            gr = await http.get(f"{ENV_URL}/grade")
            score = gr.json().get("score", 0.0)

        except Exception as e:
            score = rewards[-1] if rewards else 0.0
            print(f"[DEBUG] Error: {e}", flush=True)

    success = score >= SUCCESS_THR
    log_end(success, steps, score, rewards)


async def main():
    for task_id in TASKS:
        await run_task(task_id)



async def run_random_baseline(task_id: str):
    """Random agent — verifies reward signal is meaningful."""
    import random as _random
    rewards = []
    steps = 0
    async with httpx.AsyncClient(timeout=60) as http:
        try:
            r = await http.post(f"{ENV_URL}/reset?task_id={task_id}")
            obs = r.json()["observation"]
            for step in range(1, MAX_STEPS + 1):
                if obs.get("done"): break
                subj = _random.choice(obs["subjects"])
                action = {"subject": subj, "hours": 2.0, "session_type": "new_material"}
                r = await http.post(f"{ENV_URL}/step", json=action)
                data = r.json()
                obs = data["observation"]
                rewards.append(data.get("reward", 0.0))
                steps = step
                if data.get("done"): break
            gr = await http.get(f"{ENV_URL}/grade")
            score = gr.json().get("score", 0.0)
            print(f"[RANDOM_BASELINE] task={task_id} steps={steps} score={score:.2f} rewards={chr(44).join(f'{r:.2f}' for r in rewards)}", flush=True)
            return score
        except Exception as e:
            print(f"[RANDOM_BASELINE] task={task_id} error={e}", flush=True)
            return 0.0


async def main_with_baselines():
    print("=== RANDOM AGENT BASELINES ===", flush=True)
    for task_id in TASKS:
        await run_random_baseline(task_id)
    print("=== SMART AGENT ===", flush=True)
    for task_id in TASKS:
        await run_task(task_id)
if __name__ == "__main__":
    asyncio.run(main_with_baselines())
