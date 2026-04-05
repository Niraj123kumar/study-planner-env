"""
Unit tests for Study Planner OpenEnv
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.study_planner_env_environment import StudyPlannerEnvironment
from models import StudyPlannerAction


def test_reset_returns_clean_state():
    env = StudyPlannerEnvironment(task_id="easy")
    obs = env.reset()
    assert obs.total_hours_left == 18.0
    assert obs.done == False
    assert all(v == 0.0 for v in obs.coverage_pct.values())
    assert all(v == 0.0 for v in obs.fatigue_level.values())
    print("✅ test_reset_returns_clean_state")


def test_step_reduces_budget():
    env = StudyPlannerEnvironment(task_id="easy")
    env.reset()
    obs = env.step(StudyPlannerAction(subject="Math", hours=2.0))
    assert obs.total_hours_left == 16.0
    print("✅ test_step_reduces_budget")


def test_invalid_subject_returns_zero_reward():
    env = StudyPlannerEnvironment(task_id="easy")
    env.reset()
    obs = env.step(StudyPlannerAction(subject="InvalidSubject", hours=2.0))
    assert obs.reward == 0.0
    print("✅ test_invalid_subject_returns_zero_reward")


def test_fatigue_increases_on_repeated_study():
    env = StudyPlannerEnvironment(task_id="easy")
    env.reset()
    env.step(StudyPlannerAction(subject="Math", hours=2.0))
    obs = env.step(StudyPlannerAction(subject="Math", hours=2.0))
    assert obs.fatigue_level["Math"] > 0.0
    print("✅ test_fatigue_increases_on_repeated_study")


def test_dependency_locked_gives_low_reward():
    env = StudyPlannerEnvironment(task_id="hard")
    env.reset()
    # Biology requires Chemistry — studying Biology first should give low reward
    obs = env.step(StudyPlannerAction(subject="Biology", hours=2.0))
    assert obs.reward <= 0.1
    print("✅ test_dependency_locked_gives_low_reward")


def test_grade_returns_zero_to_one():
    env = StudyPlannerEnvironment(task_id="medium")
    env.reset()
    for _ in range(5):
        env.step(StudyPlannerAction(subject="Math", hours=2.0))
    score = env.grade()
    assert 0.0 <= score <= 1.0
    print("✅ test_grade_returns_zero_to_one")


def test_extreme_task_is_hard():
    env = StudyPlannerEnvironment(task_id="extreme")
    env.reset()
    # Naive agent — always study Math
    for _ in range(20):
        obs = env.step(StudyPlannerAction(subject="Math", hours=2.0))
        if obs.done:
            break
    score = env.grade()
    assert score < 0.5, f"Extreme task too easy: {score}"
    print(f"✅ test_extreme_task_is_hard (score={score})")


def test_retention_decay_applies():
    env = StudyPlannerEnvironment(task_id="hard")
    env.reset()
    env.step(StudyPlannerAction(subject="Math", hours=4.0))
    retention_after_study = env._retention["Math"]
    # Study other subjects to trigger decay
    for _ in range(5):
        env.step(StudyPlannerAction(subject="Chemistry", hours=2.0))
    retention_after_decay = env._retention["Math"]
    assert retention_after_decay < retention_after_study
    print(f"✅ test_retention_decay_applies ({retention_after_study:.2f} -> {retention_after_decay:.2f})")


if __name__ == "__main__":
    test_reset_returns_clean_state()
    test_step_reduces_budget()
    test_invalid_subject_returns_zero_reward()
    test_fatigue_increases_on_repeated_study()
    test_dependency_locked_gives_low_reward()
    test_grade_returns_zero_to_one()
    test_extreme_task_is_hard()
    test_retention_decay_applies()
    print("\n✅ All tests passed!")
