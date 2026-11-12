"""Application settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://gateway:gateway@localhost:5432/gateway"
    SECRET_KEY: str = "dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    LOG_LEVEL: str = "info"
    # Open Policy Agent sidecar
    OPA_URL: str = "http://localhost:8181"
    OPA_POLICY_PATH: str = "/v1/data/gateway/allow"
    # Microsoft Agent Governance Toolkit (AGT) reference alternative engine.
    # Path to the AGT ACS policy manifest (YAML). Empty = AGT not configured.
    AGT_POLICY_MANIFEST: str = ""
    # Policy engine dry-run (simulate) mode: when true, policy decisions are
    # evaluated and logged but never enforced (calls always proceed).
    POLICY_DRY_RUN: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
