from __future__ import annotations

from cua_lark.domain.models import ActionKind, TestCase


BASE_ACTIONS = [
    ActionKind.CLICK.value,
    ActionKind.TYPE_TEXT.value,
    ActionKind.HOTKEY.value,
    ActionKind.WAIT.value,
    ActionKind.SCROLL.value,
]


def infer_allowed_actions(case: TestCase) -> list[str]:
    product = (case.product or "").strip().lower()
    if product == "docs":
        return _infer_docs_allowed_actions(case)
    if product in {"im", "messenger", "chat"}:
        return _infer_im_allowed_actions(case)
    if product in {"calendar", "mail", "base", "vc"}:
        return _all_actions()
    return list(BASE_ACTIONS)


def merge_allowed_actions(explicit: list[str], inferred: list[str]) -> list[str]:
    return _dedupe([*_normalize_many(explicit), *_normalize_many(inferred)])


def _all_actions() -> list[str]:
    """Return all action kinds — used for products that should have no action restrictions."""
    return [kind.value for kind in ActionKind if kind != ActionKind.FINISHED]


def _infer_docs_allowed_actions(case: TestCase) -> list[str]:
    text = _case_text(case)
    actions = list(BASE_ACTIONS)
    actions.append(ActionKind.BATCH.value)
    if _contains_any(
        text,
        [
            "指定文本",
            "局部文本",
            "局部短语",
            "短句",
            "词语",
            "选中",
            "选择",
            "复制",
            "粘贴",
            "移动",
            "拖拽",
            "评论",
            "批注",
            "链接",
            "表格",
            "加粗",
            "高亮",
            "删除",
            "替换",
            "copy",
            "paste",
            "move",
            "drag",
            "comment",
            "link",
            "table",
            "bold",
            "highlight",
            "delete",
            "replace",
            "exact",
            "partial",
        ],
    ):
        actions.append(ActionKind.DRAG.value)
    if _contains_any(
        text,
        [
            "打开",
            "进入",
            "切换",
            "搜索结果",
            "文档结果",
            "列表",
            "最近",
            "分割线",
            "divider",
            "open",
            "entry",
            "switch",
            "result",
            "row",
        ],
    ):
        actions.append(ActionKind.DOUBLE_CLICK.value)
    if _contains_any(text, ["右键", "上下文", "context menu", "right click"]):
        actions.append(ActionKind.RIGHT_CLICK.value)
    return _dedupe(actions)


def _infer_im_allowed_actions(case: TestCase) -> list[str]:
    text = _case_text(case)
    actions = list(BASE_ACTIONS)
    if _contains_any(text, ["右键", "回复", "标记", "表情回应", "context menu", "right click", "reply", "reaction"]):
        actions.append(ActionKind.RIGHT_CLICK.value)
    if _contains_any(text, ["双击", "打开会话", "double click"]):
        actions.append(ActionKind.DOUBLE_CLICK.value)
    if _contains_any(text, ["拖拽", "drag"]):
        actions.append(ActionKind.DRAG.value)
    return _dedupe(actions)


def _case_text(case: TestCase) -> str:
    return " ".join([case.id, case.name, case.instruction, case.expected, case.stage, case.phase]).lower()


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(item.lower() in text for item in needles)


def _normalize_many(values: list[str]) -> list[str]:
    return [_normalize_action(item) for item in values if _normalize_action(item)]


def _normalize_action(value: str) -> str:
    aliases = {
        "type": ActionKind.TYPE_TEXT.value,
        "type_text": ActionKind.TYPE_TEXT.value,
        "left_double": ActionKind.DOUBLE_CLICK.value,
        "double_click": ActionKind.DOUBLE_CLICK.value,
        "right_single": ActionKind.RIGHT_CLICK.value,
        "right_click": ActionKind.RIGHT_CLICK.value,
    }
    key = (value or "").strip().lower()
    return aliases.get(key, key)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
