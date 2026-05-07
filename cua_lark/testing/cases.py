from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cua_lark.domain.models import TestCase
from cua_lark.runtime.config import NEW_ROOT
from cua_lark.testing.action_policy import infer_allowed_actions, merge_allowed_actions


def load_cases(path: Path, case_ids: list[str] | None = None, stages: list[str] | None = None) -> list[TestCase]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    raw_cases = data.get("test_cases") if isinstance(data, dict) else None
    if raw_cases is None and isinstance(data, list):
        raw_cases = data
    if not isinstance(raw_cases, list):
        raise ValueError(f"No test_cases list found in {path}")

    stage_case_ids = _case_ids_for_stages(data, stages or [])
    selected_ids = set(case_ids or [])
    if stage_case_ids:
        selected_ids.update(stage_case_ids)

    cases = [_to_case(item) for item in raw_cases if isinstance(item, dict)]
    if selected_ids:
        cases = [case for case in cases if case.id in selected_ids]
    return cases


def _case_ids_for_stages(data: dict[str, Any], stages: list[str]) -> set[str]:
    if not stages:
        return set()
    wanted = set(stages)
    found: set[str] = set()
    for stage in data.get("test_stages") or []:
        if isinstance(stage, dict) and stage.get("id") in wanted:
            found.update(str(item) for item in stage.get("cases") or [])
    return found


def _to_case(item: dict[str, Any]) -> TestCase:
    explicit_allowed_actions = [str(value) for value in item.get("allowed_actions") or []]
    instruction = _expand_workspace_vars(str(item.get("instruction") or ""))
    expected = _expand_workspace_vars(str(item.get("expected") or ""))
    base_case = TestCase(
        id=str(item["id"]),
        name=str(item.get("name") or item["id"]),
        instruction=instruction,
        expected=expected,
        product=_infer_product(item, instruction, expected),
        phase=str(item.get("phase") or ""),
        stage=str(item.get("test_stage") or ""),
        verification=dict(item.get("verification") or {}),
        explicit_allowed_actions=explicit_allowed_actions,
        input_materials=_load_input_materials(item.get("input_materials") or []),
        setup_instruction=_expand_workspace_vars(str(item.get("setup_instruction") or "")),
        setup_expected=_expand_workspace_vars(str(item.get("setup_expected") or "")),
        setup_max_steps=int(item.get("setup_max_steps") or 6),
    )
    inferred_allowed_actions = infer_allowed_actions(base_case)
    base_case.allowed_actions = merge_allowed_actions(explicit_allowed_actions, inferred_allowed_actions)
    base_case.action_policy_source = _action_policy_source(explicit_allowed_actions, inferred_allowed_actions)
    return base_case


def _infer_product(item: dict[str, Any], instruction: str, expected: str) -> str:
    explicit = str(item.get("product") or "").strip()
    if explicit:
        return explicit
    text = " ".join(
        [
            str(item.get("id") or ""),
            str(item.get("name") or ""),
            str(item.get("test_stage") or ""),
            instruction,
            expected,
        ]
    ).lower()
    if any(token in text for token in ["docs", "云文档", "文档", "docx", "markdown"]):
        return "Docs"
    if any(token in text for token in ["im", "消息", "聊天", "会话", "群聊", "私聊", "飞书消息"]):
        return "IM"
    return ""


def _action_policy_source(explicit: list[str], inferred: list[str]) -> str:
    if explicit and inferred:
        return "merged"
    if explicit:
        return "explicit"
    return "inferred"


def _expand_workspace_vars(value: str) -> str:
    replacements = {
        "{{NEW_ROOT}}": str(NEW_ROOT),
        "{{PROJECT_ROOT}}": str(NEW_ROOT),
        "{{ASSETS_DIR}}": str(NEW_ROOT / "assets"),
    }
    for key, replacement in replacements.items():
        value = value.replace(key, replacement)
    return value


def _load_input_materials(raw_materials: Any) -> list[dict[str, str]]:
    if not isinstance(raw_materials, list):
        return []
    materials: list[dict[str, str]] = []
    for index, item in enumerate(raw_materials, start=1):
        if isinstance(item, str):
            path = Path(_expand_workspace_vars(item))
            label = path.name or f"material-{index}"
            content = path.read_text(encoding="utf-8")
        elif isinstance(item, dict):
            path_text = str(item.get("path") or "")
            label = str(item.get("label") or Path(path_text).name or f"material-{index}")
            path = Path(_expand_workspace_vars(path_text)) if path_text else None
            content = str(item.get("content") or "")
            if path and path.exists():
                content = path.read_text(encoding="utf-8")
        else:
            continue
        materials.append(
            {
                "label": label,
                "path": str(path) if path else "",
                "content": content,
            }
        )
    return materials
