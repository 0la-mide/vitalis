from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    env: str = "dev"  # dev | test | prod
    database_url: str = "postgresql+asyncpg://vitalis:vitalis_dev@localhost:5432/vitalis"
    test_database_url: str = "postgresql+asyncpg://vitalis:vitalis_dev@localhost:5432/vitalis_test"

    jwt_secret: str = Field(default="dev-only-change-me-0123456789abcdef0123456789")
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    cookie_secure: bool = False  # True in prod (HTTPS)

    public_base_url: str = "http://localhost:3000"
    model_url: str = "http://localhost:8100"
    model_timeout_ms: int = 800

    upload_dir: Path = BACKEND_DIR / "var" / "uploads"

    # Matching
    city_speed_kmh: float = 25.0
    overdue_grace_minutes: int = 30
    overdue_check_seconds: int = 60

    # The team's trained risk models (diabetes, heart). Off => clinical rules only.
    enable_ncs_models: bool = True
    ncs_model_dir: str = ""

    # LLM (doctor summaries only; Phase 7)
    allow_external_llm: bool = False
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # Web push (Phase 4 completion)
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.org"

    # SMS: console (dev) | termii | bulksmsnigeria. Sender ID: 3-11 letters/digits, registered with the provider.
    sms_provider: str = "console"
    sms_sender_id: str = "VITALIS"
    termii_api_key: str = ""
    termii_base_url: str = "https://v3.api.termii.com"
    termii_channel: str = "generic"  # "dnd" once Termii activates transactional routing on the account
    bulksmsnigeria_api_token: str = ""
    bulksmsnigeria_gateway: str = "direct-refund"

    rate_limit_enabled: bool = True

    # One-tap "open a demo patient's phone" on /card (synthetic data only). Staff always use email + password.
    # On by default: this is a demo build. Set DEMO_LOGINS=false before any real pilot.
    demo_logins: bool = True

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def demo_logins_enabled(self) -> bool:
        return self.demo_logins


@lru_cache
def get_settings() -> Settings:
    return Settings()
