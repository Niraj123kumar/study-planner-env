"""
Data models for the Study Planner OpenEnv Environment.
"""
from typing import Dict, List, Optional
from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class StudyPlannerAction(Action):
    """Agent action: allocate hours to a subject."""
    subject: str = Field(..., description="Subject to allocate study hours to")
    hours: float = Field(..., ge=0.0, le=12.0, description="Hours to allocate (0-12)")
    session_type: str = Field(default="new_material", description="One of: new_material, review, practice")


class StudyPlannerObservation(Observation):
    """What the agent sees after each step."""
    subjects: List[str] = Field(default_factory=list)
    hours_remaining: Dict[str, float] = Field(default_factory=dict, description="Hours still needed per subject")
    days_until_exam: Dict[str, int] = Field(default_factory=dict, description="Days before each exam")
    total_hours_left: float = Field(default=0.0, description="Remaining study budget")
    message: str = Field(default="")
    study_history: Dict[str, List[float]] = Field(default_factory=dict, description="Past allocations per subject")
    session_count: Dict[str, int] = Field(default_factory=dict, description="Number of sessions per subject")
    fatigue_level: Dict[str, float] = Field(default_factory=dict, description="Fatigue 0.0-1.0 per subject")
    coverage_pct: Dict[str, float] = Field(default_factory=dict, description="Current retained coverage 0-1")
    retention: Dict[str, float] = Field(default_factory=dict, description="Retained knowledge 0-1 per subject")
    mock_exam_result: Optional[Dict[str, float]] = Field(default=None, description="Mock exam scores if triggered")
    exam_schedule_changed: bool = Field(default=False, description="True if an exam moved earlier this step")
    dependency_unlocked: Dict[str, bool] = Field(default_factory=dict, description="Whether subject dependencies are met")
    available_session_types: Dict[str, List[str]] = Field(default_factory=dict, description="Valid session types per subject")
