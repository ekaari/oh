"""AI Test Planner — converts natural language missions into structured test plans."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import settings
from app.core.security import generate_id, sanitize_for_prompt


DEFAULT_OBJECTIVES = [
    "Discover reachable pages and build an application map",
    "Validate navigation and broken links",
    "Exercise primary forms with positive and negative inputs",
    "Monitor console errors and uncaught exceptions",
    "Monitor network anomalies (4xx/5xx)",
    "Capture screenshots for failures and unexpected states",
]


def _heuristic_cases(mission_text: str, base_url: str) -> list[dict[str, Any]]:
    text = mission_text.lower()
    cases: list[dict[str, Any]] = [
        {
            "title": "Open base URL and capture initial state",
            "description": f"Navigate to {base_url}, wait for network idle, screenshot landing page.",
            "category": "Navigation",
        },
        {
            "title": "Discover pages and build application map",
            "description": "Crawl same-origin links, record titles and paths.",
            "category": "Navigation",
        },
        {
            "title": "Detect interactive forms and validate inputs",
            "description": "Find forms; run required-field, invalid format, and special character checks.",
            "category": "Validation",
        },
        {
            "title": "UI smoke checks",
            "description": "Check for broken buttons, empty critical regions, and inaccessible primary CTAs.",
            "category": "UI/UX",
        },
        {
            "title": "Console & network health",
            "description": "Collect console.error/warn and anomalous HTTP responses.",
            "category": "JavaScript",
        },
    ]

    if any(k in text for k in ("login", "auth", "sign in", "masuk")):
        cases.insert(
            1,
            {
                "title": "Authentication flow validation",
                "description": "Attempt configured login and verify post-login state.",
                "category": "Authentication",
            },
        )
    if any(k in text for k in ("user", "pengguna", "crud", "management")):
        cases.append(
            {
                "title": "User management happy path",
                "description": "Explore user list/create/edit surfaces without destructive deletes.",
                "category": "Functional",
            }
        )
    if any(k in text for k in ("checkout", "payment", "bayar", "cart")):
        cases.append(
            {
                "title": "Checkout flow exploration (non-destructive)",
                "description": "Walk cart/checkout UI without submitting real payments.",
                "category": "Functional",
            }
        )
    return cases


async def _llm_plan(mission_text: str, base_url: str) -> dict[str, Any] | None:
    if not settings.openai_api_key:
        return None

    safe_mission = sanitize_for_prompt(mission_text)
    prompt = f"""You are an AI QA Test Planner. Convert the mission into a JSON test plan.
Base URL: {base_url}
Mission: {safe_mission}

Return ONLY JSON:
{{
  "objectives": ["..."],
  "cases": [
    {{"title": "...", "description": "...", "category": "Functional|UI/UX|Validation|Navigation|Authentication|JavaScript|Network"}}
  ]
}}
Rules: no destructive actions, no real payments, max 10 cases, prefer exploratory + validation coverage.
"""
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "messages": [
                        {"role": "system", "content": "You output strict JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{[\s\S]*\}", content)
            if not match:
                return None
            return json.loads(match.group(0))
    except Exception:
        return None


async def create_test_plan(mission_text: str, base_url: str) -> dict[str, Any]:
    llm = await _llm_plan(mission_text, base_url)
    if llm and isinstance(llm.get("cases"), list) and llm["cases"]:
        objectives = llm.get("objectives") or DEFAULT_OBJECTIVES
        cases = llm["cases"]
    else:
        objectives = DEFAULT_OBJECTIVES
        cases = _heuristic_cases(mission_text, base_url)

    return {
        "id": generate_id("plan"),
        "objectives": objectives,
        "cases": [
            {
                "id": generate_id("case"),
                "title": c.get("title", "Untitled case"),
                "description": c.get("description"),
                "category": c.get("category", "Functional"),
                "order_index": i,
            }
            for i, c in enumerate(cases)
        ],
    }
