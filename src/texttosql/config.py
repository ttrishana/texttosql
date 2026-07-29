"""Central configuration, loaded from environment / .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- LLM (Gemini) ----
    # Free-tier request quotas are tiny and vary by key/project (often only
    # gemini-2.5-flash has any allocation, ~20/day; 2.0-flash and 2.5-pro may be 0).
    # Check https://ai.dev/rate-limit. Enable billing for real iterative use; on a
    # paid key, gemini-2.5-pro gives the strongest SQL — set it for MAIN.
    google_api_key: str = ""
    gemini_model_main: str = "gemini-2.5-flash"
    gemini_model_fast: str = "gemini-2.5-flash"

    # ---- Database ----
    admin_database_url: str = (
        "postgresql+psycopg://texttosql_admin:admin_pw@localhost:5432/firmdb"
    )
    readonly_database_url: str = (
        "postgresql+psycopg://texttosql_readonly:readonly_pw@localhost:5432/firmdb"
    )

    # ---- Local testing without Docker: embedded Postgres via pgserver ----
    # When true, the admin/readonly engines ignore the *_database_url values above
    # and run a pip-installed embedded Postgres rooted at `embedded_pgdata`.
    embedded_db: bool = False
    embedded_pgdata: str = ".pgdata"

    # ---- Multi-database mode ----
    # When true, the agent routes each question to one of the domain databases
    # declared in knowledge/sources.yaml. When false, one "firm" database is used.
    multi_db: bool = False

    # ---- Agent behavior ----
    max_correction_attempts: int = 3
    result_row_cap: int = 1000
    statement_timeout_ms: int = 15000
    retrieval_mode: bool = False

    # ---- API ----
    api_key: str = ""

    # ---- Observability ----
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "texttosql"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()
