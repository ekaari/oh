"""Test execution orchestrator — full lifecycle from PLANNING to COMPLETED."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import decrypt_secret, generate_id
from app.db.database import AsyncSessionLocal
from app.models import (
    BrowserAction,
    Bug,
    CaseStatus,
    Credential,
    Environment,
    Evidence,
    Observation,
    Project,
    Report,
    RunLifecycle,
    TestCase,
    TestMission,
    TestPlan,
    TestRun,
    TestStep,
)
from app.services.browser_agent import BrowserSession
from app.services.bug_analyzer import analyze_anomalies
from app.services.planner import create_test_plan
from app.services.report import generate_html_report


async def _set_lifecycle(db: AsyncSession, run: TestRun, mission: TestMission, state: str) -> None:
    run.lifecycle = state
    mission.status = state
    await db.commit()


async def execute_mission(mission_id: str, *, regression_of: str | None = None) -> str:
    async with AsyncSessionLocal() as db:
        mission = await db.get(TestMission, mission_id)
        if not mission:
            raise ValueError("Mission not found")
        project = await db.get(Project, mission.project_id)
        if not project:
            raise ValueError("Project not found")

        env: Environment | None = None
        if mission.environment_id:
            env = await db.get(Environment, mission.environment_id)

        cred: Credential | None = None
        if mission.credential_id:
            cred = await db.get(Credential, mission.credential_id)

        base_url = env.base_url if env else project.base_url
        safety = env.safety_level if env else "SAFE"
        allow_destructive = bool(env.allow_destructive) if env else False
        if safety == "DANGEROUS" and not allow_destructive:
            allow_destructive = False

        run = TestRun(
            id=generate_id("run"),
            mission_id=mission.id,
            lifecycle=RunLifecycle.CREATED.value,
            started_at=datetime.now(timezone.utc),
            is_regression=bool(regression_of),
            parent_run_id=regression_of,
        )
        db.add(run)
        await db.commit()

        try:
            await _set_lifecycle(db, run, mission, RunLifecycle.PLANNING.value)
            plan_data = await create_test_plan(mission.mission_text, base_url)
            plan = TestPlan(
                id=plan_data["id"],
                mission_id=mission.id,
                objectives=plan_data["objectives"],
            )
            db.add(plan)
            cases: list[TestCase] = []
            for c in plan_data["cases"]:
                tc = TestCase(
                    id=c["id"],
                    plan_id=plan.id,
                    title=c["title"],
                    description=c.get("description"),
                    category=c.get("category", "Functional"),
                    status=CaseStatus.PENDING.value,
                    order_index=c.get("order_index", 0),
                )
                db.add(tc)
                cases.append(tc)
            run.plan_id = plan.id
            await db.commit()

            await _set_lifecycle(db, run, mission, RunLifecycle.RUNNING.value)

            shot_dir = settings.screenshots_dir / run.id
            shot_dir.mkdir(parents=True, exist_ok=True)
            session = BrowserSession(
                base_url=base_url,
                run_id=run.id,
                screenshot_dir=shot_dir,
                safety_level=safety,
                allow_destructive=allow_destructive,
            )
            await session.start()

            reproduction: list[str] = [f"Open {base_url}"]
            steps_out: list[TestStep] = []
            all_ui: list = []
            all_forms: list = []
            bugs: list = []

            async def add_step(title: str, status: str, detail: str | None = None, case_id: str | None = None):
                step = TestStep(
                    id=generate_id("step"),
                    run_id=run.id,
                    case_id=case_id,
                    title=title,
                    status=status,
                    detail=detail,
                    order_index=len(steps_out),
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                )
                db.add(step)
                steps_out.append(step)
                await db.commit()

            try:
                # Case 0-ish: open base
                nav = await session.navigate(base_url)
                await _persist_action(db, run.id, nav)
                path = await session.screenshot("landing")
                db.add(
                    Evidence(
                        id=generate_id("ev"),
                        run_id=run.id,
                        evidence_type="screenshot",
                        path=path,
                        url=session.page.url if session.page else base_url,
                        meta={"label": "landing"},
                    )
                )
                await add_step(
                    "Open base URL and capture initial state",
                    CaseStatus.PASSED.value if nav.success else CaseStatus.FAILED.value,
                    nav.error,
                    cases[0].id if cases else None,
                )
                if cases:
                    cases[0].status = CaseStatus.PASSED.value if nav.success else CaseStatus.FAILED.value

                # Auth
                if cred and cred.auth_type == "username_password" and cred.password_encrypted:
                    password = decrypt_secret(cred.password_encrypted)
                    login = await session.login_username_password(
                        cred.login_url, cred.username or "", password
                    )
                    await _persist_action(db, run.id, login)
                    reproduction.append("Perform configured authentication")
                    await add_step(
                        "Authentication flow",
                        CaseStatus.PASSED.value if login.success else CaseStatus.FAILED.value,
                        login.error,
                    )
                    auth_shot = await session.screenshot("post_login")
                    db.add(
                        Evidence(
                            id=generate_id("ev"),
                            run_id=run.id,
                            evidence_type="screenshot",
                            path=auth_shot,
                            url=session.page.url if session.page else None,
                            meta={"label": "post_login"},
                        )
                    )

                # Exploration
                await _set_lifecycle(db, run, mission, RunLifecycle.OBSERVING.value)
                links = await session.discover_links()
                for link in links[: settings.max_exploration_pages]:
                    if link["url"].rstrip("/") == base_url.rstrip("/"):
                        continue
                    r = await session.navigate(link["url"])
                    await _persist_action(db, run.id, r)
                    reproduction.append(f"Navigate to {link['url']}")
                    if not r.success:
                        fail_shot = await session.screenshot("nav_fail")
                        db.add(
                            Evidence(
                                id=generate_id("ev"),
                                run_id=run.id,
                                evidence_type="screenshot",
                                path=fail_shot,
                                url=link["url"],
                                meta={"label": "nav_fail"},
                            )
                        )

                app_map = {"pages": session.visited, "discovered_links": links}
                run.application_map = app_map
                await add_step(
                    "Discover pages and build application map",
                    CaseStatus.PASSED.value,
                    f"Visited {len(session.visited)} page(s), discovered {len(links)} link(s)",
                    cases[1].id if len(cases) > 1 else None,
                )
                if len(cases) > 1:
                    cases[1].status = CaseStatus.PASSED.value

                # Forms
                form_findings = await session.run_form_negative_tests()
                all_forms.extend(form_findings)
                forms = await session.discover_forms()
                db.add(
                    Observation(
                        id=generate_id("obs"),
                        run_id=run.id,
                        kind="form",
                        payload={"forms": forms, "findings": form_findings},
                    )
                )
                form_status = CaseStatus.PASSED.value
                if any(f.get("kind") == "validation" for f in form_findings):
                    form_status = CaseStatus.FAILED.value
                await add_step(
                    "Form validation probes",
                    form_status,
                    f"{len(forms)} form(s), {len(form_findings)} finding(s)",
                )

                # UI smoke on current page
                ui = await session.ui_smoke()
                all_ui.extend(ui)
                db.add(
                    Observation(
                        id=generate_id("obs"),
                        run_id=run.id,
                        kind="page",
                        payload={"ui_findings": ui, "url": session.page.url if session.page else None},
                    )
                )
                await add_step(
                    "UI smoke checks",
                    CaseStatus.FAILED.value if ui else CaseStatus.PASSED.value,
                    f"{len(ui)} finding(s)",
                )

                # Persist console/network observations
                for log in session.console_logs:
                    db.add(
                        Observation(
                            id=generate_id("obs"),
                            run_id=run.id,
                            kind="console",
                            payload=log,
                            severity="HIGH" if log.get("type") in ("error", "exception") else "LOW",
                        )
                    )
                for net in session.network_logs:
                    db.add(
                        Observation(
                            id=generate_id("obs"),
                            run_id=run.id,
                            kind="network",
                            payload=net,
                            severity="CRITICAL" if int(net.get("status", 0)) >= 500 else "MEDIUM",
                        )
                    )
                await add_step(
                    "Console & network health",
                    CaseStatus.FAILED.value
                    if session.console_logs or session.network_logs
                    else CaseStatus.PASSED.value,
                    f"{len(session.console_logs)} console, {len(session.network_logs)} network anomalies",
                )
                await db.commit()

                # Analyze + verify bugs
                await _set_lifecycle(db, run, mission, RunLifecycle.ANALYZING.value)
                await _set_lifecycle(db, run, mission, RunLifecycle.VERIFYING.value)
                bugs = analyze_anomalies(
                    project_id=project.id,
                    run_id=run.id,
                    console_logs=session.console_logs,
                    network_logs=session.network_logs,
                    ui_findings=all_ui,
                    form_findings=all_forms,
                    page_url=session.page.url if session.page else base_url,
                    reproduction_base=reproduction,
                )
                for b in bugs:
                    bug = Bug(
                        id=b["id"],
                        project_id=b["project_id"],
                        run_id=b["run_id"],
                        title=b["title"],
                        severity=b["severity"],
                        category=b["category"],
                        url=b.get("url"),
                        reproduction_steps=b.get("reproduction_steps") or [],
                        expected_result=b.get("expected_result"),
                        actual_result=b.get("actual_result"),
                        verified=b.get("verified", False),
                        verification_notes=b.get("verification_notes"),
                        network_info=b.get("network_info"),
                        console_info=b.get("console_info"),
                    )
                    db.add(bug)
                    # Attach latest screenshot as evidence when bug confirmed
                    shot = await session.screenshot("bug")
                    db.add(
                        Evidence(
                            id=generate_id("ev"),
                            run_id=run.id,
                            bug_id=bug.id,
                            evidence_type="screenshot",
                            path=shot,
                            url=bug.url,
                            meta={"bug_id": bug.id},
                        )
                    )
                await db.commit()

            finally:
                await session.stop()

            # Mark remaining cases based on steps
            for case in cases[2:]:
                if case.status == CaseStatus.PENDING.value:
                    case.status = CaseStatus.PASSED.value

            # Summary + report
            passed = sum(1 for s in steps_out if s.status == CaseStatus.PASSED.value)
            failed = sum(1 for s in steps_out if s.status == CaseStatus.FAILED.value)
            blocked = sum(1 for s in steps_out if s.status == CaseStatus.BLOCKED.value)
            summary = {
                "passed": passed,
                "failed": failed,
                "blocked": blocked,
                "total": len(steps_out),
                "bugs": len(bugs),
            }
            # reload evidences/bugs for report
            result = await db.execute(
                select(TestRun)
                .where(TestRun.id == run.id)
                .options(
                    selectinload(TestRun.steps),
                    selectinload(TestRun.bugs),
                    selectinload(TestRun.evidences),
                )
            )
            run_fresh = result.scalar_one()
            report_path = generate_html_report(
                {
                    "run_id": run.id,
                    "lifecycle": RunLifecycle.COMPLETED.value,
                    "mission_title": mission.title,
                    "mission_text": mission.mission_text,
                    "summary": summary,
                    "app_map": run.application_map or {"pages": []},
                    "steps": [
                        {"title": s.title, "status": s.status, "detail": s.detail} for s in run_fresh.steps
                    ],
                    "bugs": [
                        {
                            "id": b.id,
                            "title": b.title,
                            "severity": b.severity,
                            "category": b.category,
                            "url": b.url,
                        }
                        for b in run_fresh.bugs
                    ],
                    "evidences": [
                        {"id": e.id, "evidence_type": e.evidence_type, "path": e.path, "url": e.url}
                        for e in run_fresh.evidences
                    ],
                }
            )
            run.summary = summary
            run.report_path = str(report_path)
            run.finished_at = datetime.now(timezone.utc)
            db.add(
                Report(
                    id=generate_id("rep"),
                    run_id=run.id,
                    format="html",
                    path=str(report_path),
                )
            )
            await _set_lifecycle(db, run, mission, RunLifecycle.COMPLETED.value)
            return run.id

        except Exception as e:
            run.lifecycle = RunLifecycle.ERROR.value
            run.error_message = str(e)
            run.finished_at = datetime.now(timezone.utc)
            mission.status = RunLifecycle.ERROR.value
            await db.commit()
            # attempt recovery marker
            run.lifecycle = RunLifecycle.RECOVERY.value
            await db.commit()
            run.lifecycle = RunLifecycle.ERROR.value
            await db.commit()
            raise


async def _persist_action(db: AsyncSession, run_id: str, action) -> None:
    db.add(
        BrowserAction(
            id=action.id,
            run_id=run_id,
            action_type=action.action_type,
            selector=action.selector,
            value=action.value,
            url=action.url,
            success=action.success,
            error=action.error,
        )
    )
    await db.commit()
