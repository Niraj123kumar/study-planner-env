import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import StudyPlannerAction, StudyPlannerObservation
from server.study_planner_env_environment import StudyPlannerEnvironment
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Study Planner OpenEnv", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

_env_store = {}

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/web")
async def web_ui(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/web")
async def web_ui(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/")
@app.get("/health")
def health():
    return {"status": "healthy", "env": "study-planner-env"}

@app.post("/reset")
async def reset(task_id: str = "easy"):
    env = StudyPlannerEnvironment(task_id=task_id)
    _env_store["env"] = env
    obs = env.reset()
    return {"observation": obs.dict(), "reward": 0.0, "done": False, "task_id": task_id}

import json as _json
from openai import OpenAI as _OpenAI

def _get_llm_action(obs_dict: dict, available_subjects: list) -> dict:
    _api_base = os.environ.get("API_BASE_URL", "")
    _api_key  = os.environ.get("API_KEY") or os.environ.get("HF_TOKEN", "")
    _model    = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
    if not _api_base or not _api_key:
        return None
    try:
        _client = _OpenAI(base_url=_api_base, api_key=_api_key)
        prompt = f"""You are a study planning agent.
Current state:
{_json.dumps(obs_dict, indent=2)}
Choose the best next study action. Reply ONLY with valid JSON:
{{"subject": "<subject>", "hours": <float 0.5-4.0>, "session_type": "<new_material|review|practice>"}}
Only use subjects from: {available_subjects}"""
        resp = _client.chat.completions.create(
            model=_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        return _json.loads(raw)
    except Exception as e:
        print(f"LLM error: {e}", flush=True)
        return None

@app.post("/step")
async def step(action: StudyPlannerAction):
    env = _env_store.get("env")
    if env is None:
        return JSONResponse({"error": "Call /reset first"}, status_code=400)
    # Ask LLM for action; if it returns a valid one, use it instead
    try:
        subjects = env._cfg["subjects"]
        allocated = env._allocated
        required  = env._cfg["required_hours"]
        obs_dict = {
            "subjects": subjects,
            "coverage_pct": {s: round(allocated[s] / max(required[s], 1), 3) for s in subjects},
            "days_until_exam": dict(env._cfg["days_until_exam"]),
            "fatigue_level": dict(env._fatigue),
            "total_hours_left": env._hours_budget,
        }
        llm_action = _get_llm_action(obs_dict, subjects)
        if llm_action and llm_action.get("subject") in subjects:
            action = StudyPlannerAction(**llm_action)
    except Exception as e:
        print(f"LLM step error: {e}", flush=True)
    obs = env.step(action)
    return {"observation": obs.dict(), "reward": obs.reward, "done": obs.done, "info": {}}

@app.get("/state")
def state():
    env = _env_store.get("env")
    if env is None:
        return JSONResponse({"error": "Call /reset first"}, status_code=400)
    s = env.state
    return {"task_id": env.task_id, "step_count": s.step_count, "episode_id": s.episode_id}

@app.get("/grade")
def grade():
    env = _env_store.get("env")
    if env is None:
        return JSONResponse({"error": "Call /reset first"}, status_code=400)
    return {"score": env.grade()}

def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
