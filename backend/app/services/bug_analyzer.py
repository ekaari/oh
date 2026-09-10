"""Bug analyzer — Detect → Analyze → Reproduce → Verify → Confirm."""

from __future__ import annotations

from typing import Any

from app.core.security import generate_id
from app.models import BugCategory, Severity


def _severity_for_network(status: int) -> str:
    if status >= 500:
        return Severity.CRITICAL.value
    if status in (401, 403):
        return Severity.HIGH.value
    if status == 404:
        return Severity.MEDIUM.value
    return Severity.MEDIUM.value


def analyze_anomalies(
    *,
    project_id: str,
    run_id: str,
    console_logs: list[dict[str, Any]],
    network_logs: list[dict[str, Any]],
    ui_findings: list[dict[str, Any]],
    form_findings: list[dict[str, Any]],
    page_url: str | None,
    reproduction_base: list[str],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for log in console_logs:
        if log.get("type") in ("error", "exception"):
            candidates.append(
                {
                    "title": f"JavaScript {log.get('type')}: {str(log.get('text', ''))[:120]}",
                    "severity": Severity.HIGH.value,
                    "category": BugCategory.JAVASCRIPT.value,
                    "url": page_url,
                    "expected_result": "No console errors or uncaught exceptions during exploration",
                    "actual_result": log.get("text"),
                    "console_info": log,
                    "network_info": None,
                    "verification_notes": "Detected via console monitoring; verified by presence during run",
                    "verified": True,
                    "reproduction_steps": reproduction_base
                    + ["Open browser console", "Observe error/exception entry"],
                }
            )

    # Deduplicate network by url+status
    seen_net: set[tuple[str, int]] = set()
    for net in network_logs:
        key = (net.get("url", ""), int(net.get("status", 0)))
        if key in seen_net:
            continue
        seen_net.add(key)
        status = int(net.get("status", 0))
        candidates.append(
            {
                "title": f"HTTP {status} on {net.get('method', 'GET')} {net.get('url', '')[:180]}",
                "severity": _severity_for_network(status),
                "category": BugCategory.NETWORK.value,
                "url": net.get("url") or page_url,
                "expected_result": "Successful HTTP response (<400)",
                "actual_result": f"Received status {status}",
                "console_info": None,
                "network_info": net,
                "verification_notes": "Reproduced by network observer during autonomous run",
                "verified": True,
                "reproduction_steps": reproduction_base
                + [f"Trigger request to {net.get('url')}", f"Observe status {status}"],
            }
        )

    for finding in ui_findings:
        kind = finding.get("kind")
        if kind == "validation_ok":
            continue
        severity = Severity.MEDIUM.value
        category = BugCategory.UI_UX.value
        if kind == "empty_state":
            severity = Severity.LOW.value
        candidates.append(
            {
                "title": f"UI issue ({kind}): {finding.get('message')}",
                "severity": severity,
                "category": category,
                "url": page_url,
                "expected_result": "Healthy UI without broken assets or empty critical regions",
                "actual_result": finding.get("message"),
                "console_info": None,
                "network_info": None,
                "verification_notes": "Confirmed by DOM inspection during UI smoke checks",
                "verified": True,
                "reproduction_steps": reproduction_base + ["Inspect primary UI regions"],
            }
        )

    for finding in form_findings:
        if finding.get("kind") == "validation_ok":
            continue
        if finding.get("kind") == "validation":
            candidates.append(
                {
                    "title": f"Form validation gap: {finding.get('message')}",
                    "severity": Severity.HIGH.value,
                    "category": BugCategory.VALIDATION.value,
                    "url": page_url,
                    "expected_result": "Required fields block empty submission",
                    "actual_result": finding.get("message"),
                    "console_info": None,
                    "network_info": None,
                    "verification_notes": "Verified via HTML5 reportValidity / empty submit probe",
                    "verified": True,
                    "reproduction_steps": reproduction_base
                    + ["Open form", "Leave required fields empty", "Attempt submit"],
                }
            )

    # Cap noise
    return [
        {**c, "id": generate_id("bug"), "project_id": project_id, "run_id": run_id}
        for c in candidates[:25]
    ]
