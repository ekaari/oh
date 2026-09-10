from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import encrypt_secret, generate_id, mask_sensitive
from app.db.database import get_db
from app.models import (
    Bug,
    Credential,
    Environment,
    Evidence,
    Project,
    TestCase,
    TestMission,
    TestPlan,
    TestRun,
    TestStep,
)
from app.schemas import (
    CredentialCreate,
    CredentialOut,
    DashboardStats,
    EnvironmentCreate,
    EnvironmentOut,
    MissionCreate,
    MissionOut,
    NLQueryRequest,
    NLQueryResponse,
    ProjectCreate,
    ProjectOut,
    TestPlanOut,
    TestRunOut,
)
from app.services.runner import execute_mission

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    projects = await db.scalar(select(func.count()).select_from(Project)) or 0
    missions = await db.scalar(select(func.count()).select_from(TestMission)) or 0
    runs = await db.scalar(select(func.count()).select_from(TestRun)) or 0
    steps = (await db.execute(select(TestStep.status, func.count()).group_by(TestStep.status))).all()
    counts = {s: c for s, c in steps}
    sev_rows = (await db.execute(select(Bug.severity, func.count()).group_by(Bug.severity))).all()
    return DashboardStats(
        projects=projects,
        missions=missions,
        runs=runs,
        tests_total=sum(counts.values()),
        tests_passed=counts.get("PASSED", 0),
        tests_failed=counts.get("FAILED", 0),
        tests_blocked=counts.get("BLOCKED", 0),
        bugs_by_severity={s: c for s, c in sev_rows},
    )


@router.post("/projects", response_model=ProjectOut)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)) -> Project:
    project = Project(
        id=generate_id("proj"),
        name=payload.name,
        description=payload.description,
        base_url=payload.base_url,
    )
    db.add(project)
    # default staging environment
    db.add(
        Environment(
            id=generate_id("env"),
            project_id=project.id,
            name="Staging",
            env_type="Staging",
            base_url=payload.base_url,
            safety_level="SAFE",
        )
    )
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[Project]:
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.post("/projects/{project_id}/environments", response_model=EnvironmentOut)
async def create_environment(
    project_id: str, payload: EnvironmentCreate, db: AsyncSession = Depends(get_db)
) -> Environment:
    if not await db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    env = Environment(
        id=generate_id("env"),
        project_id=project_id,
        name=payload.name,
        env_type=payload.env_type,
        base_url=payload.base_url,
        safety_level=payload.safety_level,
        allow_destructive=payload.allow_destructive,
    )
    db.add(env)
    await db.commit()
    await db.refresh(env)
    return env


@router.get("/projects/{project_id}/environments", response_model=list[EnvironmentOut])
async def list_environments(project_id: str, db: AsyncSession = Depends(get_db)) -> list[Environment]:
    result = await db.execute(
        select(Environment).where(Environment.project_id == project_id).order_by(Environment.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/projects/{project_id}/credentials", response_model=CredentialOut)
async def create_credential(
    project_id: str, payload: CredentialCreate, db: AsyncSession = Depends(get_db)
) -> CredentialOut:
    if not await db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    cred = Credential(
        id=generate_id("cred"),
        project_id=project_id,
        name=payload.name,
        auth_type=payload.auth_type,
        username=payload.username,
        password_encrypted=encrypt_secret(payload.password) if payload.password else None,
        token_encrypted=encrypt_secret(payload.token) if payload.token else None,
        cookies_encrypted=encrypt_secret(payload.cookies) if payload.cookies else None,
        login_url=payload.login_url,
        custom_flow=payload.custom_flow,
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return CredentialOut(
        id=cred.id,
        project_id=cred.project_id,
        name=cred.name,
        auth_type=cred.auth_type,
        username=cred.username,
        login_url=cred.login_url,
        has_password=bool(cred.password_encrypted),
        has_token=bool(cred.token_encrypted),
        has_cookies=bool(cred.cookies_encrypted),
        created_at=cred.created_at,
    )


@router.get("/projects/{project_id}/credentials", response_model=list[CredentialOut])
async def list_credentials(project_id: str, db: AsyncSession = Depends(get_db)) -> list[CredentialOut]:
    result = await db.execute(
        select(Credential).where(Credential.project_id == project_id).order_by(Credential.created_at.desc())
    )
    items = []
    for cred in result.scalars().all():
        items.append(
            CredentialOut(
                id=cred.id,
                project_id=cred.project_id,
                name=cred.name,
                auth_type=cred.auth_type,
                username=cred.username,
                login_url=cred.login_url,
                has_password=bool(cred.password_encrypted),
                has_token=bool(cred.token_encrypted),
                has_cookies=bool(cred.cookies_encrypted),
                created_at=cred.created_at,
            )
        )
    return items


@router.post("/projects/{project_id}/missions", response_model=MissionOut)
async def create_mission(
    project_id: str, payload: MissionCreate, db: AsyncSession = Depends(get_db)
) -> TestMission:
    if not await db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    mission = TestMission(
        id=generate_id("mis"),
        project_id=project_id,
        environment_id=payload.environment_id,
        credential_id=payload.credential_id,
        title=payload.title,
        mission_text=payload.mission_text,
    )
    db.add(mission)
    await db.commit()
    await db.refresh(mission)
    return mission


@router.get("/projects/{project_id}/missions", response_model=list[MissionOut])
async def list_missions(project_id: str, db: AsyncSession = Depends(get_db)) -> list[TestMission]:
    result = await db.execute(
        select(TestMission).where(TestMission.project_id == project_id).order_by(TestMission.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/missions/{mission_id}", response_model=MissionOut)
async def get_mission(mission_id: str, db: AsyncSession = Depends(get_db)) -> TestMission:
    mission = await db.get(TestMission, mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")
    return mission


@router.post("/missions/{mission_id}/start")
async def start_mission(
    mission_id: str, background: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    mission = await db.get(TestMission, mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")
    background.add_task(_run_safe, mission_id)
    return {"status": "started", "mission_id": mission_id}


@router.post("/runs/{run_id}/retest")
async def retest(run_id: str, background: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    run = await db.get(TestRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    background.add_task(_run_safe, run.mission_id, run_id)
    return {"status": "started", "mission_id": run.mission_id, "parent_run_id": run_id}


async def _run_safe(mission_id: str, regression_of: str | None = None) -> None:
    try:
        await execute_mission(mission_id, regression_of=regression_of)
    except Exception:
        # errors persisted inside execute_mission
        pass


@router.get("/missions/{mission_id}/runs", response_model=list[TestRunOut])
async def list_runs(mission_id: str, db: AsyncSession = Depends(get_db)) -> list[TestRun]:
    result = await db.execute(
        select(TestRun)
        .where(TestRun.mission_id == mission_id)
        .options(
            selectinload(TestRun.steps),
            selectinload(TestRun.bugs),
            selectinload(TestRun.evidences),
            selectinload(TestRun.actions),
            selectinload(TestRun.observations),
        )
        .order_by(TestRun.started_at.desc())
    )
    return list(result.scalars().all())


@router.get("/runs/{run_id}", response_model=TestRunOut)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)) -> TestRun:
    result = await db.execute(
        select(TestRun)
        .where(TestRun.id == run_id)
        .options(
            selectinload(TestRun.steps),
            selectinload(TestRun.bugs),
            selectinload(TestRun.evidences),
            selectinload(TestRun.actions),
            selectinload(TestRun.observations),
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/missions/{mission_id}/plans", response_model=list[TestPlanOut])
async def list_plans(mission_id: str, db: AsyncSession = Depends(get_db)) -> list[TestPlan]:
    result = await db.execute(
        select(TestPlan)
        .where(TestPlan.mission_id == mission_id)
        .options(selectinload(TestPlan.cases))
        .order_by(TestPlan.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/projects/{project_id}/bugs")
async def list_bugs(project_id: str, db: AsyncSession = Depends(get_db)) -> list[Any]:
    result = await db.execute(
        select(Bug).where(Bug.project_id == project_id).order_by(Bug.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/files/{evidence_id}")
async def get_evidence_file(evidence_id: str, db: AsyncSession = Depends(get_db)):
    ev = await db.get(Evidence, evidence_id)
    if not ev or not ev.path:
        raise HTTPException(404, "Evidence not found")
    return FileResponse(ev.path)


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await db.get(TestRun, run_id)
    if not run or not run.report_path:
        raise HTTPException(404, "Report not found")
    return FileResponse(run.report_path, media_type="text/html")


@router.post("/query", response_model=NLQueryResponse)
async def nl_query(payload: NLQueryRequest, db: AsyncSession = Depends(get_db)) -> NLQueryResponse:
    q = payload.question.lower()
    sources: list[str] = []

    if payload.run_id:
        result = await db.execute(
            select(TestRun)
            .where(TestRun.id == payload.run_id)
            .options(selectinload(TestRun.bugs), selectinload(TestRun.steps))
        )
        run = result.scalar_one_or_none()
        if not run:
            raise HTTPException(404, "Run not found")
        sources.append(run.id)
        if "serious" in q or "critical" in q or "serius" in q:
            crit = [b for b in run.bugs if b.severity in ("CRITICAL", "HIGH")]
            if not crit:
                return NLQueryResponse(answer="Tidak ada bug CRITICAL/HIGH pada run ini.", sources=sources)
            lines = [f"- [{b.severity}] {b.title}" for b in crit[:5]]
            return NLQueryResponse(answer="Bug paling serius:\n" + "\n".join(lines), sources=sources)
        if "fail" in q or "gagal" in q:
            fails = [s for s in run.steps if s.status == "FAILED"]
            if not fails:
                return NLQueryResponse(answer="Tidak ada step yang FAILED.", sources=sources)
            lines = [f"- {s.title}: {s.detail or ''}" for s in fails]
            return NLQueryResponse(answer="Test yang gagal:\n" + "\n".join(lines), sources=sources)
        if "regression" in q:
            return NLQueryResponse(
                answer=f"Run ini {'merupakan' if run.is_regression else 'bukan'} regression re-test."
                + (f" Parent: {run.parent_run_id}" if run.parent_run_id else ""),
                sources=sources,
            )
        summary = run.summary or {}
        return NLQueryResponse(
            answer=(
                f"Lifecycle={run.lifecycle}. Passed={summary.get('passed', 0)}, "
                f"Failed={summary.get('failed', 0)}, Bugs={len(run.bugs)}."
            ),
            sources=sources,
        )

    # project-level
    bugs_q = select(Bug)
    if payload.project_id:
        bugs_q = bugs_q.where(Bug.project_id == payload.project_id)
    bugs = list((await db.execute(bugs_q.order_by(Bug.created_at.desc()).limit(10))).scalars().all())
    sources = [b.id for b in bugs]
    if not bugs:
        return NLQueryResponse(answer="Belum ada bug tercatat.", sources=[])
    lines = [f"- [{b.severity}] {b.title}" for b in bugs]
    return NLQueryResponse(answer="Ringkasan bug terbaru:\n" + "\n".join(lines), sources=sources)
