from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Web Tester"
    app_version: str = "1.0.0"
    api_prefix: str = "/api"
    secret_key: str = "change-me-in-production-ai-web-tester-secret"
    storage_dir: Path = Path(__file__).resolve().parents[2] / "storage"
    database_url: str = ""
    screenshots_dir: Path = storage_dir / "screenshots"
    reports_dir: Path = storage_dir / "reports"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    playwright_headless: bool = True
    max_exploration_pages: int = 8
    max_form_tests: int = 5
    browser_timeout_ms: int = 30000
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
settings.reports_dir.mkdir(parents=True, exist_ok=True)
if not settings.database_url:
    settings.database_url = f"sqlite+aiosqlite:///{settings.storage_dir / 'ai_web_tester.db'}"
