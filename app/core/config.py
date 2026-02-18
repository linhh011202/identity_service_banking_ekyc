import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


def _load_yaml_config() -> dict:
    """Load configuration from config.yaml file.

    The path is resolved in order:
      1. CONFIG_PATH environment variable (used by Cloud Run secret mount)
      2. config.yaml at the project root (local development)
    """
    config_path = Path(
        os.environ.get("CONFIG_PATH")
        or Path(__file__).resolve().parents[2] / "config.yaml"
    )
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


_raw = _load_yaml_config()


@dataclass(frozen=True)
class Configs:
    # Project name
    PROJECT_NAME: str = _raw.get("project_name", "")

    # API
    API: str = _raw.get("api", {}).get("prefix", "/api")
    API_V1_STR: str = _raw.get("api", {}).get("v1_prefix", "/api/v1")

    # Database config
    POSTGRES_USER: str = os.environ.get("POSTGRES_USER") or _raw.get(
        "database", {}
    ).get("user", "")
    POSTGRES_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD") or _raw.get(
        "database", {}
    ).get("password", "")
    POSTGRES_DB: str = os.environ.get("POSTGRES_DB") or _raw.get("database", {}).get(
        "db", ""
    )
    POSTGRES_HOST: str = os.environ.get("POSTGRES_HOST") or _raw.get(
        "database", {}
    ).get("host", "")
    POSTGRES_PORT: int = int(
        os.environ.get("POSTGRES_PORT") or _raw.get("database", {}).get("port", 5432)
    )

    # Other config
    TZ: str = _raw.get("timezone", "Asia/Singapore")

    # BACKEND_CORS_ORIGINS
    BACKEND_CORS_ORIGINS: List[str] = field(
        default_factory=lambda: _raw.get("cors", {}).get("origins", ["*"])
    )

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


configs = Configs()
