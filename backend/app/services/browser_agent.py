"""Playwright browser controller with observation hooks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, Page, async_playwright

from app.core.config import settings
from app.core.security import generate_id, mask_sensitive


ERROR_STATUS = {400, 401, 403, 404, 409, 422, 500, 502, 503, 504}


@dataclass
class ActionRecord:
    id: str
    action_type: str
    selector: str | None = None
    value: str | None = None
    url: str | None = None
    success: bool = True
    error: str | None = None


@dataclass
class BrowserSession:
    base_url: str
    run_id: str
    screenshot_dir: Path
    safety_level: str = "SAFE"
    allow_destructive: bool = False
    page: Page | None = None
    browser: Browser | None = None
    _playwright: Any = None
    console_logs: list[dict[str, Any]] = field(default_factory=list)
    network_logs: list[dict[str, Any]] = field(default_factory=list)
    actions: list[ActionRecord] = field(default_factory=list)
    visited: list[dict[str, Any]] = field(default_factory=list)

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(headless=settings.playwright_headless)
        context = await self.browser.new_context(ignore_https_errors=True)
        self.page = await context.new_page()
        self.page.set_default_timeout(settings.browser_timeout_ms)

        self.page.on("console", self._on_console)
        self.page.on("pageerror", self._on_page_error)
        self.page.on("response", self._on_response)

    def _on_console(self, msg) -> None:
        if msg.type in ("error", "warning"):
            self.console_logs.append(
                {
                    "type": msg.type,
                    "text": msg.text[:1000],
                    "location": str(msg.location) if msg.location else None,
                }
            )

    def _on_page_error(self, exc) -> None:
        self.console_logs.append({"type": "exception", "text": str(exc)[:1000]})

    async def _on_response(self, response) -> None:
        try:
            status = response.status
            if status >= 400 or status in ERROR_STATUS:
                self.network_logs.append(
                    {
                        "url": response.url,
                        "status": status,
                        "method": response.request.method,
                        "resource_type": response.request.resource_type,
                    }
                )
        except Exception:
            pass

    async def stop(self) -> None:
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()

    def _record(self, **kwargs) -> ActionRecord:
        rec = ActionRecord(id=generate_id("act"), **kwargs)
        self.actions.append(rec)
        return rec

    def _is_destructive_selector(self, selector: str | None, value: str | None = None) -> bool:
        blob = f"{selector or ''} {value or ''}".lower()
        patterns = ("delete", "remove", "destroy", "drop ", "hapus", "payment", "checkout submit", "purchase")
        return any(p in blob for p in patterns)

    async def navigate(self, url: str) -> ActionRecord:
        assert self.page
        target = url if url.startswith("http") else urljoin(self.base_url, url)
        try:
            await self.page.goto(target, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(500)
            title = await self.page.title()
            self.visited.append({"url": self.page.url, "title": title})
            return self._record(action_type="navigate", url=self.page.url, success=True)
        except Exception as e:
            return self._record(action_type="navigate", url=target, success=False, error=str(e))

    async def screenshot(self, label: str = "state") -> str:
        assert self.page
        path = self.screenshot_dir / f"{self.run_id}_{label}_{generate_id('shot')}.png"
        await self.page.screenshot(path=str(path), full_page=True)
        return str(path)

    async def click(self, selector: str) -> ActionRecord:
        assert self.page
        if not self.allow_destructive and self._is_destructive_selector(selector):
            return self._record(
                action_type="click",
                selector=selector,
                success=False,
                error=f"Blocked by safety guardrail ({self.safety_level})",
            )
        try:
            await self.page.click(selector, timeout=8000)
            return self._record(action_type="click", selector=selector, url=self.page.url)
        except Exception as e:
            return self._record(action_type="click", selector=selector, success=False, error=str(e))

    async def type_text(self, selector: str, value: str, mask: bool = False) -> ActionRecord:
        assert self.page
        display = mask_sensitive(value) if mask else value
        try:
            await self.page.fill(selector, value)
            return self._record(action_type="type", selector=selector, value=display, url=self.page.url)
        except Exception as e:
            return self._record(
                action_type="type", selector=selector, value=display, success=False, error=str(e)
            )

    async def discover_links(self, limit: int | None = None) -> list[dict[str, str]]:
        assert self.page
        limit = limit or settings.max_exploration_pages
        origin = urlparse(self.base_url).netloc
        hrefs = await self.page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.href, text: (e.innerText||'').trim().slice(0,80)}))",
        )
        seen: set[str] = set()
        results: list[dict[str, str]] = []
        for item in hrefs:
            href = item.get("href") or ""
            if not href or href.startswith(("javascript:", "mailto:", "tel:")):
                continue
            parsed = urlparse(href)
            if parsed.netloc and parsed.netloc != origin:
                continue
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean in seen:
                continue
            seen.add(clean)
            results.append({"url": clean, "text": item.get("text") or clean})
            if len(results) >= limit:
                break
        return results

    async def discover_forms(self) -> list[dict[str, Any]]:
        assert self.page
        return await self.page.evaluate(
            """() => Array.from(document.querySelectorAll('form')).slice(0, 10).map((form, idx) => {
              const fields = Array.from(form.querySelectorAll('input, select, textarea')).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || el.tagName.toLowerCase(),
                name: el.getAttribute('name') || el.getAttribute('id') || '',
                required: el.required || el.getAttribute('aria-required') === 'true',
                placeholder: el.getAttribute('placeholder') || ''
              }));
              return {
                index: idx,
                action: form.getAttribute('action') || '',
                method: (form.getAttribute('method') || 'get').toLowerCase(),
                fields
              };
            })"""
        )

    async def ui_smoke(self) -> list[dict[str, Any]]:
        assert self.page
        return await self.page.evaluate(
            """() => {
              const findings = [];
              const buttons = Array.from(document.querySelectorAll('button, [role=button], a.btn, input[type=submit]'));
              const disabledVisible = buttons.filter(b => {
                const style = window.getComputedStyle(b);
                return style.display !== 'none' && style.visibility !== 'hidden' && (b.disabled || b.getAttribute('aria-disabled') === 'true');
              });
              if (buttons.length === 0) findings.push({kind: 'missing_cta', message: 'No primary buttons/links found'});
              const images = Array.from(document.images).filter(img => !img.complete || img.naturalWidth === 0);
              if (images.length) findings.push({kind: 'broken_image', message: `${images.length} image(s) failed to load`});
              const emptyMain = document.querySelector('main, #root, #app, .content');
              if (emptyMain && (emptyMain.innerText || '').trim().length < 5) {
                findings.push({kind: 'empty_state', message: 'Primary content region appears empty'});
              }
              return findings;
            }"""
        )

    async def login_username_password(
        self, login_url: str | None, username: str, password: str
    ) -> ActionRecord:
        assert self.page
        target = login_url or self.base_url
        await self.navigate(target)
        # Heuristic selectors — never log raw password
        user_selectors = [
            'input[type="email"]',
            'input[name*="user" i]',
            'input[name*="email" i]',
            'input[id*="user" i]',
            'input[id*="email" i]',
            'input[type="text"]',
        ]
        pass_selectors = ['input[type="password"]']
        filled_user = False
        for sel in user_selectors:
            if await self.page.locator(sel).count() > 0:
                await self.type_text(sel, username, mask=False)
                filled_user = True
                break
        filled_pass = False
        for sel in pass_selectors:
            if await self.page.locator(sel).count() > 0:
                await self.type_text(sel, password, mask=True)
                filled_pass = True
                break
        if not filled_user or not filled_pass:
            return self._record(
                action_type="login",
                success=False,
                error="Could not locate username/password fields",
                url=self.page.url,
            )
        submit = 'button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign in")'
        try:
            if await self.page.locator(submit).count() > 0:
                await self.page.locator(submit).first.click()
            else:
                await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(1500)
            return self._record(action_type="login", success=True, url=self.page.url)
        except Exception as e:
            return self._record(action_type="login", success=False, error=str(e), url=self.page.url)

    async def run_form_negative_tests(self) -> list[dict[str, Any]]:
        assert self.page
        findings: list[dict[str, Any]] = []
        forms = await self.discover_forms()
        for form in forms[: settings.max_form_tests]:
            required = [f for f in form.get("fields", []) if f.get("required") and f.get("name")]
            if not required:
                continue
            # Submit empty required form via JS without navigating away if possible
            try:
                result = await self.page.evaluate(
                    """(idx) => {
                      const form = document.querySelectorAll('form')[idx];
                      if (!form) return {ok:false, reason:'missing'};
                      const before = location.href;
                      if (typeof form.reportValidity === 'function') {
                        const valid = form.reportValidity();
                        return {ok:true, clientValid: valid, url: location.href, before};
                      }
                      return {ok:true, clientValid: null, url: location.href, before};
                    }""",
                    form["index"],
                )
                if result.get("clientValid") is True:
                    findings.append(
                        {
                            "kind": "validation",
                            "message": f"Form #{form['index']} reported valid with empty required fields",
                            "form": form,
                        }
                    )
                elif result.get("clientValid") is False:
                    findings.append(
                        {
                            "kind": "validation_ok",
                            "message": f"Form #{form['index']} correctly blocks empty required fields",
                            "form": form,
                        }
                    )
            except Exception as e:
                findings.append({"kind": "form_error", "message": str(e), "form": form})
        return findings
