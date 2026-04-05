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

@app.post("/step")
async def step(action: StudyPlannerAction):
    env = _env_store.get("env")
    if env is None:
        return JSONResponse({"error": "Call /reset first"}, status_code=400)
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
