"""
inference.py — Study Planner OpenEnv Baseline Inference Script
"""

import asyncio
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI
from models import StudyPlannerAction
from server.study_planner_env_environment import StudyPlannerEnvironment

HF_TOKEN     = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
BENCHMARK    = "study-planner-env"
TASKS        = ["easy", "medium", "hard"]
MAX_STEPS    = 18

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

def get_action(obs_dict: dict) -> dict:
    prompt = f"""You are a smart study planner agent.

Current state:
{json.dumps(obs_dict, indent=2)}

Choose the best next study action. Reply ONLY with valid JSON in this exact format:
{{"subject": "<subject name>", "hours": <float 0.5-4.0>, "session_type": "<new_material|review|practice>"}}

Rules:
- Only use subjects listed in obs["subjects"]
- Use "practice" only if coverage_pct for that subject >= 0.5
- Prioritize subjects with low coverage and exams soon
- Keep hours between 0.5 and 4.0"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.2,
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        action = json.loads(raw)
        assert "subject" in action and "hours" in action and "session_type" in action
        return action
    except Exception:
        subjects = obs_dict.get("subjects", ["Math"])
        return {"subject": subjects[0], "hours": 2.0, "session_type": "new_material"}

def run_task(task_id: str):
    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)
    rewards = []
    steps = 0
    score = 0.0
    success = False
    try:
        env = StudyPlannerEnvironment(task_id=task_id)
        obs = env.reset()
        for step in range(1, MAX_STEPS + 1):
            if obs.done:
                break
            obs_dict = {
                "subjects": obs.subjects,
                "coverage_pct": obs.coverage_pct,
                "days_until_exam": obs.days_until_exam,
                "fatigue_level": obs.fatigue_level,
                "total_hours_left": obs.total_hours_left,
                "hours_remaining": obs.hours_remaining,
            }
            action_dict = get_action(obs_dict)
            action = StudyPlannerAction(**action_dict)
            obs = env.step(action)
            reward = obs.reward
            done = obs.done
            rewards.append(reward)
            steps += 1
            print(f"[STEP] step={step} action={json.dumps(action_dict)} reward={reward:.2f} done={str(done).lower()} error=null", flush=True)
            if done:
                break
        score = env.grade()
        success = score > 0.1
    except Exception as e:
        print(f"[STEP] step={steps+1} action=null reward=0.00 done=true error={e}", flush=True)
        score = 0.0
        success = False
    rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else "0.00"
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

def main():
    for task in TASKS:
        run_task(task)

if __name__ == "__main__":
    main()

def run(input_data):
    main()
    return {"output": "ok"}
