from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from cua_lark.domain.models import RunInfo


def create_run(root: Path, suite: str, round_name: str | None = None) -> RunInfo:
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    round_slug = _slug(round_name or "round")
    round_id = f"{round_slug}-{stamp}"
    run_root = root / round_id
    cases_dir = run_root / "cases"
    cases_dir.mkdir(parents=True, exist_ok=False)
    return RunInfo(
        suite=suite,
        round_id=round_id,
        root=run_root,
        cases_dir=cases_dir,
        started_at=started,
    )


def case_dir_name(case_id: str, name: str) -> str:
    return f"{_slug(case_id)}__{_slug(name)[:48]}"


def _slug(value: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", value.strip(), flags=re.UNICODE)
    return text.strip("-") or "run"
