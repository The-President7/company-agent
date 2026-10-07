"""Environment-backed configuration; secrets never belong in the repository."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./secretary.db")
    workspace_id: str = os.getenv("COMPANY_WORKSPACE_ID", "the-president")
    workspace_name: str = os.getenv("COMPANY_WORKSPACE_NAME", "The President")
    user_id: str = os.getenv("APP_USER_ID", "local-admin")
    user_name: str = os.getenv("APP_USER_NAME", "Local admin")
    seed_demo_data: bool = os.getenv("SEED_DEMO_DATA", "true").lower() in {"1", "true", "yes"}
    api_token: str = os.getenv("API_AUTH_TOKEN", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    slack_bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_repositories: str = os.getenv("GITHUB_REPOSITORIES", "")
    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    whatsapp_app_secret: str = os.getenv("WHATSAPP_APP_SECRET", "")
    whatsapp_phone_number_ids: str = os.getenv("WHATSAPP_PHONE_NUMBER_IDS", "")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "")
    alert_webhook_url: str = os.getenv("ALERT_WEBHOOK_URL", "")
    alert_threshold: int = int(os.getenv("ALERT_THRESHOLD", "10"))
    monitor_allowed_origins: str = os.getenv("MONITOR_ALLOWED_ORIGINS", "*")


settings = Settings()
