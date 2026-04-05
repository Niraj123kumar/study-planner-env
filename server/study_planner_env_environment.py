"""
Study Planner Environment — Core Logic
Tasks: easy, medium, hard, extreme
Version: 2.1.0
"""
import sys, os, copy, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Dict, List, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State
from models import StudyPlannerAction, StudyPlannerObservation

TASK_CONFIGS: Dict[str, Dict[str, Any]] = {
    "easy": {
        "subjects": ["Math", "Physics", "Chemistry"],
        "required_hours": {"Math": 6.0, "Physics": 4.0, "Chemistry": 3.0},
        "days_until_exam": {"Math": 5, "Physics": 7, "Chemistry": 6},
        "hours_budget": 18.0,
        "max_steps": 12,  # ~3 study sessions/day × 4 days before exams
        "priority_weights": {"Math": 1.2, "Physics": 1.0, "Chemistry": 0.9},
        "blocked_steps": [],
        "penalty_subjects": [],
        "dependencies": {},
        "mock_exam_step": None,
        "surprise_subject": None,
        "min_coverage_threshold": 0.0,
        "fatigue_decay": 0.3,
        "retention_decay_rate": 0.0,
    },
    "medium": {
        "subjects": ["Math", "Physics", "Chemistry", "Biology"],
        "required_hours": {"Math": 8.0, "Physics": 6.0, "Chemistry": 5.0, "Biology": 6.0},
        "days_until_exam": {"Math": 4, "Physics": 6, "Chemistry": 7, "Biology": 5},
        "hours_budget": 22.0,
        "max_steps": 14,  # ~2 study sessions/day × 7 days, with disruptions
        "priority_weights": {"Math": 1.3, "Physics": 1.1, "Chemistry": 0.9, "Biology": 1.0},
        "blocked_steps": [6, 7],
        "penalty_subjects": ["Biology"],
        "dependencies": {"Biology": "Chemistry"},
        "mock_exam_step": 6,
        "surprise_subject": None,
        "min_coverage_threshold": 0.3,
        "fatigue_decay": 0.4,
        "retention_decay_rate": 0.04,
    },
    "hard": {
        "subjects": ["Math", "Physics", "Chemistry", "Biology", "History"],
        "required_hours": {"Math": 10.0, "Physics": 7.0, "Chemistry": 6.0, "Biology": 7.0, "History": 5.0},
        "days_until_exam": {"Math": 3, "Physics": 4, "Chemistry": 8, "Biology": 5, "History": 9},
        "hours_budget": 24.0,
        "max_steps": 18,  # ~2 sessions/day × 9 days, harder scheduling required
        "priority_weights": {"Math": 1.5, "Physics": 1.2, "Chemistry": 0.8, "Biology": 1.0, "History": 0.6},
        "blocked_steps": [4, 5, 10, 11],
        "penalty_subjects": ["History", "Chemistry"],
        "dependencies": {"Biology": "Chemistry", "Physics": "Math"},
        "mock_exam_step": 7,
        "surprise_subject": "Physics",
        "min_coverage_threshold": 0.4,
        "fatigue_decay": 0.5,
        "retention_decay_rate": 0.05,
    },
    "extreme": {
        "subjects": ["Math", "Physics", "Chemistry", "Biology", "History", "Computer Science"],
        "required_hours": {"Math": 12.0, "Physics": 10.0, "Chemistry": 8.0, "Biology": 9.0, "History": 6.0, "Computer Science": 10.0},
        "days_until_exam": {"Math": 2, "Physics": 3, "Chemistry": 6, "Biology": 4, "History": 7, "Computer Science": 3},
        "hours_budget": 24.0,
        "max_steps": 20,  # maximum sessions before all exams begin
        "priority_weights": {"Math": 1.8, "Physics": 1.5, "Chemistry": 0.9, "Biology": 1.2, "History": 0.5, "Computer Science": 1.6},
        "blocked_steps": [3, 4, 8, 9, 14, 15],
        "penalty_subjects": ["History", "Chemistry", "Biology"],
        "dependencies": {"Biology": "Chemistry", "Physics": "Math", "Computer Science": "Math"},
        "mock_exam_step": 5,
        "surprise_subject": "Computer Science",
        "min_coverage_threshold": 0.5,
        "fatigue_decay": 0.6,
        "retention_decay_rate": 0.10,
    },
}


class StudyPlannerEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, task_id: str = "easy"):
        self.task_id = task_id if task_id in TASK_CONFIGS else "easy"
        self._cfg = copy.deepcopy(TASK_CONFIGS[self.task_id])
        self._allocated: Dict[str, float] = {}
        self._retention: Dict[str, float] = {}
        self._study_history: Dict[str, List[float]] = {}
        self._session_count: Dict[str, int] = {}
        self._fatigue: Dict[str, float] = {}
        self._last_studied_step: Dict[str, int] = {}
        self._hours_budget: float = 0.0
        self._step_count: int = 0
        self._done: bool = False
        self._final_score: Optional[float] = None
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._mock_exam_triggered: bool = False
        self._surprise_triggered: bool = False
        self._failed_min_coverage: bool = False

    def reset(self) -> StudyPlannerObservation:
        self._cfg = copy.deepcopy(TASK_CONFIGS[self.task_id])
        self._allocated = {s: 0.0 for s in self._cfg["subjects"]}
        self._retention = {s: 0.0 for s in self._cfg["subjects"]}
        self._study_history = {s: [] for s in self._cfg["subjects"]}
        self._session_count = {s: 0 for s in self._cfg["subjects"]}
        self._fatigue = {s: 0.0 for s in self._cfg["subjects"]}
        self._last_studied_step = {s: 0 for s in self._cfg["subjects"]}
        self._hours_budget = self._cfg["hours_budget"]
        self._step_count = 0
        self._done = False
        self._final_score = None
        self._mock_exam_triggered = False
        self._surprise_triggered = False
        self._failed_min_coverage = False
        self._state = State(episode_id=str(uuid4()), step_count=0)
        return self._make_obs(0.0, f"Task '{self.task_id}' started. Allocate your study hours wisely.")

    def step(self, action: StudyPlannerAction) -> StudyPlannerObservation:
        if self._done:
            return self._make_obs(0.0, "Episode already finished.")

        self._step_count += 1
        self._state.step_count = self._step_count
        extra_msgs = []

        # Apply retention decay to all subjects each step
        decay_rate = self._cfg["retention_decay_rate"]
        if decay_rate > 0:
            for s in self._cfg["subjects"]:
                steps_since = self._step_count - self._last_studied_step.get(s, 0)
                if steps_since > 2:
                    decay = decay_rate * (steps_since - 2)
                    old = self._retention[s]
                    self._retention[s] = max(0.0, self._retention[s] - decay)
                    if old > 0.3 and self._retention[s] < 0.3:
                        extra_msgs.append(f"WARNING: {s} retention dropping — needs review!")

        # Disruption
        if self._step_count in self._cfg["blocked_steps"]:
            self._hours_budget = max(0.0, self._hours_budget - 2.0)
            extra_msgs.append("DISRUPTION: Lost 2h!")

        # Exam surprise
        surprise_sub = self._cfg.get("surprise_subject")
        if surprise_sub and not self._surprise_triggered and self._step_count == 5:
            self._cfg["days_until_exam"][surprise_sub] = max(
                1, self._cfg["days_until_exam"][surprise_sub] - 2
            )
            self._surprise_triggered = True
            extra_msgs.append(f"EXAM SURPRISE: {surprise_sub} exam moved 2 days earlier!")

        # Validate subject
        if action.subject not in self._cfg["subjects"]:
            return self._make_obs(0.0, f"Invalid subject '{action.subject}'.")

        # Validate session_type
        session_type = action.session_type if action.session_type in ["new_material", "review", "practice"] else "new_material"
        coverage = self._retention.get(action.subject, 0.0)

        # Practice only allowed after 50% coverage
        if session_type == "practice" and coverage < 0.5:
            session_type = "new_material"
            extra_msgs.append(f"Practice not available for {action.subject} yet — switched to new_material.")

        # Check dependency
        dep_unlocked = self._check_dependency(action.subject)
        dep = self._cfg["dependencies"].get(action.subject)
        if dep and not dep_unlocked:
            extra_msgs.append(f"WARNING: {action.subject} requires {dep} basics first.")

        # Session type multipliers
        fatigue = self._fatigue.get(action.subject, 0.0)
        if session_type == "new_material":
            fatigue_increase = 0.25
            retention_multiplier = 1.0
            hour_efficiency = 1.0 - fatigue * 0.5
        elif session_type == "review":
            fatigue_increase = 0.10
            retention_multiplier = 0.6
            hour_efficiency = 1.0 - fatigue * 0.2
        else:  # practice
            fatigue_increase = 0.15
            retention_multiplier = 1.3
            hour_efficiency = 1.0 - fatigue * 0.3

        raw_hours = min(action.hours, self._hours_budget)
        effective_hours = raw_hours * hour_efficiency

        if raw_hours <= 0:
            self._done = True
            self._final_score = self._compute_final_score()
            return self._make_obs(0.0, "No budget remaining. Episode done.")

        # Apply study
        self._allocated[action.subject] += effective_hours
        self._study_history[action.subject].append(round(effective_hours, 2))
        self._session_count[action.subject] += 1
        self._last_studied_step[action.subject] = self._step_count
        self._hours_budget -= raw_hours

        # Update retention
        required = self._cfg["required_hours"][action.subject]
        retention_gain = (effective_hours / max(required, 1.0)) * retention_multiplier
        self._retention[action.subject] = min(1.0, self._retention[action.subject] + retention_gain)

        # Update fatigue
        for s in self._cfg["subjects"]:
            if s == action.subject:
                self._fatigue[s] = min(1.0, self._fatigue[s] + fatigue_increase)
            else:
                self._fatigue[s] = max(0.0, self._fatigue[s] - self._cfg["fatigue_decay"] * 0.1)

        reward = round(min(max(self._step_reward(action.subject, effective_hours, dep_unlocked, session_type), 0.0), 1.0), 4)

        # Mock exam
        mock_result = None
        if self._cfg.get("mock_exam_step") == self._step_count and not self._mock_exam_triggered:
            self._mock_exam_triggered = True
            mock_result = self._run_mock_exam()
            for s, score in mock_result.items():
                if score < 0.5:
                    self._cfg["priority_weights"][s] = min(2.0, self._cfg["priority_weights"][s] * 1.4)
            extra_msgs.append("MOCK EXAM triggered! Weak subjects boosted in priority.")

        if fatigue > 0.5:
            extra_msgs.append(f"HIGH FATIGUE on {action.subject} — consider switching subjects.")

        if self._step_count >= self._cfg["max_steps"] or self._hours_budget <= 0:
            self._done = True
            self._final_score = self._compute_final_score()

        msg_parts = [f"[{session_type.upper()}] Allocated {raw_hours:.1f}h to {action.subject} (effective: {effective_hours:.1f}h)."]
        msg_parts.extend(extra_msgs)
        if self._done:
            msg_parts.append(f"Episode done. Final score: {self._final_score:.2f}")

        obs = self._make_obs(reward, " ".join(msg_parts))
        if mock_result:
            obs.mock_exam_result = mock_result
        obs.metadata.update({
            "info": {
                "fatigue": {s: round(self._fatigue.get(s, 0), 2) for s in self._cfg["subjects"]},
                "retention": {s: round(self._retention.get(s, 0), 2) for s in self._cfg["subjects"]},
                "disruption_occurred": self._step_count in self._cfg["blocked_steps"],
                "mock_exam_triggered": self._mock_exam_triggered,
                "surprise_triggered": self._surprise_triggered,
                "failed_min_coverage": self._failed_min_coverage,
            }
        })
        return obs

    def _check_dependency(self, subject: str) -> bool:
        dep = self._cfg["dependencies"].get(subject)
        if not dep:
            return True
        required = self._cfg["required_hours"].get(dep, 1.0)
        allocated = self._allocated.get(dep, 0.0)
        return (allocated / max(required, 1.0)) >= 0.2

    def _run_mock_exam(self) -> Dict[str, float]:
        return {s: round(self._retention.get(s, 0.0), 2) for s in self._cfg["subjects"]}

    def grade(self) -> float:
        if self._final_score is not None:
            return round(self._final_score, 4)
        return round(self._compute_final_score(), 4)

    @property
    def state(self) -> State:
        return self._state

    def _get_available_session_types(self, subject: str) -> List[str]:
        types = ["new_material", "review"]
        if self._retention.get(subject, 0.0) >= 0.5:
            types.append("practice")
        return types

    def _make_obs(self, reward: float, message: str) -> StudyPlannerObservation:
        hours_remaining = {
            s: round(max(0.0, self._cfg["required_hours"][s] - self._allocated.get(s, 0.0)), 2)
            for s in self._cfg["subjects"]
        }
        coverage_pct = {
            s: round(self._retention.get(s, 0.0), 2)
            for s in self._cfg["subjects"]
        }
        dep_unlocked = {s: self._check_dependency(s) for s in self._cfg["subjects"]}
        available_session_types = {s: self._get_available_session_types(s) for s in self._cfg["subjects"]}

        return StudyPlannerObservation(
            subjects=self._cfg["subjects"],
            hours_remaining=hours_remaining,
            days_until_exam=self._cfg["days_until_exam"],
            total_hours_left=round(self._hours_budget, 2),
            message=message,
            done=self._done,
            reward=reward,
            metadata={"step": self._step_count, "task_id": self.task_id},
            study_history=copy.deepcopy(self._study_history),
            session_count=copy.deepcopy(self._session_count),
            fatigue_level={s: round(self._fatigue.get(s, 0.0), 2) for s in self._cfg["subjects"]},
            coverage_pct=coverage_pct,
            retention={s: round(self._retention.get(s, 0.0), 2) for s in self._cfg["subjects"]},
            mock_exam_result=None,
            exam_schedule_changed=self._surprise_triggered,
            dependency_unlocked=dep_unlocked,
            available_session_types=available_session_types,
        )

    def _step_reward(self, subject: str, effective_hours: float, dep_unlocked: bool, session_type: str) -> float:
        cfg = self._cfg
        required = cfg["required_hours"][subject]
        retention = self._retention.get(subject, 0.0)
        over = max(0.0, self._allocated.get(subject, 0.0) - required)

        if over > 0 and subject in cfg["penalty_subjects"]:
            return max(0.0, 0.03 - over * 0.08)

        if not dep_unlocked:
            return 0.05

        days = cfg["days_until_exam"][subject]
        urgency = 1.0 / max(days, 1)
        need_ratio = max(0.0, 1.0 - retention)
        weight = cfg["priority_weights"].get(subject, 1.0)
        fatigue = self._fatigue.get(subject, 0.0)

        session_bonus = {"new_material": 1.0, "review": 0.7, "practice": 1.2}.get(session_type, 1.0)
        fatigue_penalty = fatigue * 0.3

        # Synergy: studying Math helps Physics/CS, Chemistry helps Biology
        SYNERGY = {"Physics": "Math", "Biology": "Chemistry", "Computer Science": "Math"}
        syn_dep = SYNERGY.get(subject)
        synergy_bonus = 0.0
        if syn_dep:
            synergy_bonus = self._retention.get(syn_dep, 0.0) * 0.1
        raw = (urgency * 2.0 + need_ratio * 1.5) * weight * session_bonus + synergy_bonus
        return min((raw / 6.5) - fatigue_penalty, 1.0)

    def _compute_final_score(self) -> float:
        cfg = self._cfg
        weights = cfg["priority_weights"]
        total_weight = sum(weights.values())
        coverage_score = 0.0
        penalty = 0.0

        for s in cfg["subjects"]:
            retention = self._retention.get(s, 0.0)
            w = weights.get(s, 1.0)
            min_thr = cfg.get("min_coverage_threshold", 0.0)
            if min_thr > 0 and retention < min_thr:
                self._failed_min_coverage = True
            coverage_score += retention * w

            if s in cfg["penalty_subjects"]:
                allocated = self._allocated.get(s, 0.0)
                required = cfg["required_hours"][s]
                over = max(0.0, allocated - required)
                penalty += (over / max(required, 1.0)) * w * 0.7

            sessions = self._session_count.get(s, 0)
            if sessions > 3:
                penalty += 0.02 * (sessions - 3)

        coverage_score /= total_weight
        penalty /= max(total_weight, 1.0)
        total_used = sum(self._allocated.values())
        efficiency_bonus = 0.05 * (total_used / max(cfg["hours_budget"], 1.0))
        score = coverage_score - penalty + efficiency_bonus

        if self._failed_min_coverage:
            score *= 0.4

        return round(min(max(score, 0.0), 1.0), 4)
