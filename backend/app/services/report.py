"""HTML report generator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Template

from app.core.config import settings
from app.core.security import generate_id

REPORT_TEMPLATE = Template(
    """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>AI Web Tester Report — {{ run_id }}</title>
  <style>
    :root { --bg:#0f1419; --panel:#1a222c; --text:#e8eef5; --muted:#8b9bb0; --pass:#3ecf8e; --fail:#ff6b6b; --warn:#f0b429; --accent:#4cc9f0; }
    body { font-family: "IBM Plex Sans", "Segoe UI", sans-serif; background: radial-gradient(1200px 600px at 10% -10%, #1b2a3a, var(--bg)); color: var(--text); margin:0; padding:32px; }
    h1,h2,h3 { font-family: "IBM Plex Serif", Georgia, serif; letter-spacing:-0.02em; }
    .wrap { max-width: 1080px; margin: 0 auto; }
    .hero { margin-bottom: 28px; }
    .meta { color: var(--muted); font-size: 14px; }
    .grid { display:grid; grid-template-columns: repeat(4,1fr); gap:12px; margin: 20px 0 28px; }
    .stat { background: color-mix(in oklab, var(--panel) 90%, white 5%); padding:16px; border:1px solid #2a3644; }
    .stat b { display:block; font-size:28px; }
    .stat span { color: var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:0.08em; }
    section { background: var(--panel); border:1px solid #2a3644; padding:20px; margin-bottom:16px; }
    table { width:100%; border-collapse: collapse; }
    th, td { text-align:left; padding:10px 8px; border-bottom:1px solid #2a3644; vertical-align:top; font-size:14px; }
    .sev-CRITICAL,.sev-HIGH { color: var(--fail); }
    .sev-MEDIUM { color: var(--warn); }
    .sev-LOW,.sev-INFO { color: var(--accent); }
    .pass { color: var(--pass); }
    .fail { color: var(--fail); }
    img { max-width: 100%; border:1px solid #2a3644; margin-top:8px; }
    code { background:#0d1218; padding:2px 6px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>AI Web Tester Report</h1>
      <p class="meta">Run <code>{{ run_id }}</code> · {{ generated_at }} · Lifecycle: {{ lifecycle }}</p>
      <p>{{ mission_title }} — {{ mission_text }}</p>
    </div>
    <div class="grid">
      <div class="stat"><b>{{ summary.passed }}</b><span>Passed</span></div>
      <div class="stat"><b>{{ summary.failed }}</b><span>Failed</span></div>
      <div class="stat"><b>{{ summary.blocked }}</b><span>Blocked</span></div>
      <div class="stat"><b>{{ bugs|length }}</b><span>Bugs</span></div>
    </div>

    <section>
      <h2>Application Map</h2>
      <ul>
      {% for page in app_map.pages %}
        <li><code>{{ page.url }}</code> — {{ page.title }}</li>
      {% else %}
        <li>No pages recorded</li>
      {% endfor %}
      </ul>
    </section>

    <section>
      <h2>Test Steps</h2>
      <table>
        <thead><tr><th>Step</th><th>Status</th><th>Detail</th></tr></thead>
        <tbody>
        {% for s in steps %}
          <tr>
            <td>{{ s.title }}</td>
            <td class="{{ 'pass' if s.status=='PASSED' else 'fail' }}">{{ s.status }}</td>
            <td>{{ s.detail or '' }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Verified Bugs</h2>
      <table>
        <thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Category</th><th>URL</th></tr></thead>
        <tbody>
        {% for b in bugs %}
          <tr>
            <td>{{ b.id }}</td>
            <td>{{ b.title }}</td>
            <td class="sev-{{ b.severity }}">{{ b.severity }}</td>
            <td>{{ b.category }}</td>
            <td>{{ b.url or '' }}</td>
          </tr>
        {% else %}
          <tr><td colspan="5">No verified bugs</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Evidence</h2>
      {% for e in evidences %}
        <div>
          <p class="meta">{{ e.evidence_type }} · {{ e.url or '' }}</p>
          {% if e.path and e.path.endswith('.png') %}
            <img src="/api/files/{{ e.id }}" alt="evidence" />
          {% endif %}
        </div>
      {% else %}
        <p>No evidence captured</p>
      {% endfor %}
    </section>
  </div>
</body>
</html>
"""
)


def generate_html_report(payload: dict[str, Any]) -> Path:
    html = REPORT_TEMPLATE.render(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        **payload,
    )
    path = settings.reports_dir / f"report_{payload['run_id']}_{generate_id('rpt')}.html"
    path.write_text(html, encoding="utf-8")
    return path
