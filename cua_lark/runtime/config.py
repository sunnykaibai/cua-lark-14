from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


NEW_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = NEW_ROOT.parent


@dataclass
class Settings:
    repo_root: Path
    new_root: Path
    config_path: Path
    default_cases: Path
    default_scenario: Path
    default_system_prompt: Path
    results_root: Path
    output_root: Path
    vlm: dict[str, Any]
    screenshot: dict[str, Any]
    executor: dict[str, Any]


def load_settings(config_path: str | Path | None = None) -> Settings:
    _load_dotenv_candidates()
    path = Path(config_path) if config_path else NEW_ROOT / "configs" / "config.yaml"
    raw = _read_yaml(path) if path.exists() else {}
    return Settings(
        repo_root=REPO_ROOT,
        new_root=NEW_ROOT,
        config_path=path,
        default_cases=NEW_ROOT / "tests" / "test_cases" / "phase2-im.yaml",
        default_scenario=NEW_ROOT / "cua_lark" / "scenarios" / "im.md",
        default_system_prompt=NEW_ROOT / "cua_lark" / "scenarios" / "system.md",
        results_root=NEW_ROOT / "results",
        output_root=REPO_ROOT / "outputs",
        vlm=dict(raw.get("vlm") or {}),
        screenshot=dict(raw.get("screenshot") or {}),
        executor=dict(raw.get("executor") or {}),
    )


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _load_dotenv_candidates() -> None:
    for path in (
        NEW_ROOT / ".env",
        REPO_ROOT / ".env",
        REPO_ROOT / "cua-lark-14" / ".env",
    ):
        _load_dotenv(path)


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        return {}
    return data
