from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    base_url: str


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    base_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class EnvironmentCreate(BaseModel):
    name: str
    env_type: str = "Staging"
    base_url: str
    safety_level: str = "SAFE"
    allow_destructive: bool = False


class EnvironmentOut(BaseModel):
    id: str
    project_id: str
    name: str
    env_type: str
    base_url: str
    safety_level: str
    allow_destructive: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CredentialCreate(BaseModel):
    name: str
    auth_type: str = "username_password"
    username: str | None = None
    password: str | None = None
    token: str | None = None
    cookies: str | None = None
    login_url: str | None = None
    custom_flow: dict[str, Any] | None = None


class CredentialOut(BaseModel):
    id: str
    project_id: str
    name: str
    auth_type: str
    username: str | None
    login_url: str | None
    has_password: bool = False
    has_token: bool = False
    has_cookies: bool = False
    created_at: datetime


class MissionCreate(BaseModel):
    title: str
    mission_text: str
    environment_id: str | None = None
    credential_id: str | None = None


class MissionOut(BaseModel):
    id: str
    project_id: str
    environment_id: str | None
    credential_id: str | None
    title: str
    mission_text: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TestCaseOut(BaseModel):
    id: str
    plan_id: str
    title: str
    description: str | None
    category: str
    status: str
    order_index: int

    class Config:
        from_attributes = True


class TestPlanOut(BaseModel):
    id: str
    mission_id: str
    objectives: list[Any]
    cases: list[TestCaseOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class BugOut(BaseModel):
    id: str
    project_id: str
    run_id: str | None
    title: str
    severity: str
    category: str
    url: str | None
    reproduction_steps: list[Any]
    expected_result: str | None
    actual_result: str | None
    verified: bool
    verification_notes: str | None
    network_info: dict[str, Any] | None
    console_info: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


class EvidenceOut(BaseModel):
    id: str
    run_id: str
    bug_id: str | None
    evidence_type: str
    path: str | None
    url: str | None
    meta: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


class TestStepOut(BaseModel):
    id: str
    run_id: str
    case_id: str | None
    title: str
    status: str
    detail: str | None
    order_index: int

    class Config:
        from_attributes = True


class BrowserActionOut(BaseModel):
    id: str
    run_id: str
    action_type: str
    selector: str | None
    value: str | None
    url: str | None
    success: bool
    error: str | None
    timestamp: datetime

    class Config:
        from_attributes = True


class ObservationOut(BaseModel):
    id: str
    run_id: str
    kind: str
    payload: dict[str, Any]
    severity: str | None
    timestamp: datetime

    class Config:
        from_attributes = True


class TestRunOut(BaseModel):
    id: str
    mission_id: str
    plan_id: str | None
    lifecycle: str
    started_at: datetime | None
    finished_at: datetime | None
    summary: dict[str, Any] | None
    application_map: dict[str, Any] | None
    report_path: str | None
    is_regression: bool
    parent_run_id: str | None
    error_message: str | None
    steps: list[TestStepOut] = []
    bugs: list[BugOut] = []
    evidences: list[EvidenceOut] = []
    actions: list[BrowserActionOut] = []
    observations: list[ObservationOut] = []

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    projects: int
    missions: int
    runs: int
    tests_total: int
    tests_passed: int
    tests_failed: int
    tests_blocked: int
    bugs_by_severity: dict[str, int]


class NLQueryRequest(BaseModel):
    question: str
    run_id: str | None = None
    project_id: str | None = None


class NLQueryResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
