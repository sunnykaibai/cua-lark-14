from __future__ import annotations

from typing import Any

from cua_lark.domain.models import Action, ActionKind


INPUT_FOCUS_TERMS = {
    "input",
    "composer",
    "message box",
    "message area",
    "text field",
    "search box",
    "search input",
    "reply composer",
    "输入框",
    "输入区",
    "消息框",
    "编辑框",
    "搜索框",
    "回复框",
    "文本框",
}


def interpret_visual_change(action: Action | None, change: dict[str, Any]) -> dict[str, Any]:
    """Add task-level meaning to raw pixel diff observations."""
    if not action or action.kind != ActionKind.CLICK or not _is_input_focus_target(action):
        return change
    if change.get("status") not in {"no-visible-change", "small-change"}:
        return change

    interpreted = dict(change)
    interpreted["raw_status"] = change.get("status")
    interpreted["status"] = "focus-likely"
    interpreted["reason"] = "input_click_cursor_blink_or_existing_focus"
    interpreted["guidance"] = "do_not_reclick_only_because_caret_is_invisible"
    return interpreted


def is_input_focus_target(action: Action) -> bool:
    return _is_input_focus_target(action)


def _is_input_focus_target(action: Action) -> bool:
    # Use the claimed target/evidence, not generic intent words in Thought.
    # Docs body-editing thoughts often say "input cursor", which is not enough
    # to prove the click really landed in a stable text field.
    text = " ".join(
        [
            action.target or "",
            str(action.grounding.get("evidence") or ""),
        ]
    ).lower()
    return any(term.lower() in text for term in INPUT_FOCUS_TERMS)
