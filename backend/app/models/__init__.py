from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EnvType(str, Enum):
    DEVELOPMENT = "Development"
    STAGING = "Staging"
    PRODUCTION = "Production"
    LOCAL = "Local"
    CUSTOM = "Custom"


class SafetyLevel(str, Enum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    DANGEROUS = "DANGEROUS"


class AuthType(str, Enum):
    NONE = "none"
    USERNAME_PASSWORD = "username_password"
    TOKEN = "token"
    COOKIES = "cookies"
    OAUTH = "oauth"
    CUSTOM = "custom"


class CaseStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class RunLifecycle(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    OBSERVING = "OBSERVING"
    ANALYZING = "ANALYZING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    RECOVERY = "RECOVERY"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class BugCategory(str, Enum):
    FUNCTIONAL = "Functional"
    UI_UX = "UI/UX"
    VALIDATION = "Validation"
    PERFORMANCE = "Performance"
    NETWORK = "Network"
    JAVASCRIPT = "JavaScript"
    NAVIGATION = "Navigation"
    DATA = "Data"
    AUTHENTICATION = "Authentication"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    environments: Mapped[list["Environment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    credentials: Mapped[list["Credential"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    missions: Mapped[list["TestMission"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    bugs: Mapped[list["Bug"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    env_type: Mapped[str] = mapped_column(String(64), default=EnvType.STAGING.value)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    safety_level: Mapped[str] = mapped_column(String(32), default=SafetyLevel.SAFE.value)
    allow_destructive: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="environments")


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(64), default=AuthType.USERNAME_PASSWORD.value)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    cookies_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    login_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    custom_flow: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="credentials")


class TestMission(Base):
    __tablename__ = "test_missions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    environment_id: Mapped[str | None] = mapped_column(ForeignKey("environments.id"), nullable=True)
    credential_id: Mapped[str | None] = mapped_column(ForeignKey("credentials.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    mission_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=RunLifecycle.CREATED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="missions")
    plans: Mapped[list["TestPlan"]] = relationship(back_populates="mission", cascade="all, delete-orphan")
    runs: Mapped[list["TestRun"]] = relationship(back_populates="mission", cascade="all, delete-orphan")


class TestPlan(Base):
    __tablename__ = "test_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(ForeignKey("test_missions.id"), nullable=False)
    objectives: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    mission: Mapped["TestMission"] = relationship(back_populates="plans")
    cases: Mapped[list["TestCase"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("test_plans.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="Functional")
    status: Mapped[str] = mapped_column(String(32), default=CaseStatus.PENDING.value)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    plan: Mapped["TestPlan"] = relationship(back_populates="cases")


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(ForeignKey("test_missions.id"), nullable=False)
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("test_plans.id"), nullable=True)
    lifecycle: Mapped[str] = mapped_column(String(32), default=RunLifecycle.CREATED.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    application_map: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_regression: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    mission: Mapped["TestMission"] = relationship(back_populates="runs")
    steps: Mapped[list["TestStep"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    actions: Mapped[list["BrowserAction"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    observations: Mapped[list["Observation"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    bugs: Mapped[list["Bug"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class TestStep(Base):
    __tablename__ = "test_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id"), nullable=False)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("test_cases.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=CaseStatus.PENDING.value)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped["TestRun"] = relationship(back_populates="steps")


class BrowserAction(Base):
    __tablename__ = "browser_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    selector: Mapped[str | None] = mapped_column(String(512), nullable=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped["TestRun"] = relationship(back_populates="actions")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)  # console, network, page, form
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped["TestRun"] = relationship(back_populates="observations")


class Bug(Base):
    __tablename__ = "bugs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("test_runs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default=Severity.MEDIUM.value)
    category: Mapped[str] = mapped_column(String(64), default=BugCategory.FUNCTIONAL.value)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    reproduction_steps: Mapped[list] = mapped_column(JSON, default=list)
    expected_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    network_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    console_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="bugs")
    run: Mapped["TestRun"] = relationship(back_populates="bugs")
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="bug", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id"), nullable=False)
    bug_id: Mapped[str | None] = mapped_column(ForeignKey("bugs.id"), nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(64), default="screenshot")
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped["TestRun"] = relationship(back_populates="evidences")
    bug: Mapped["Bug | None"] = relationship(back_populates="evidences")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id"), nullable=False)
    format: Mapped[str] = mapped_column(String(32), default="html")
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
