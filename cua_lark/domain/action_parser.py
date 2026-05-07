from __future__ import annotations

import re
import json

from cua_lark.domain.coordinates import CoordinateSpace
from cua_lark.domain.models import Action, ActionKind, Box, Point


ACTION_LINE = re.compile(r"^Action:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
COMPLETION_CHECK_LINE = re.compile(r"^CompletionCheck:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
THOUGHT_LINE = re.compile(r"^Thought:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
EXPECTED_LINE = re.compile(r"^Expected:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
GROUNDING_LINE = re.compile(r"^Grounding:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
ELEMENTS_LINE = re.compile(r"^Elements:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
ACTIONS_LINE = re.compile(r"^Actions:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
POINT = re.compile(r"<point>\s*(\d+)\s+(\d+)\s*</point>")
BOX = re.compile(r"<(?:box|bbox)>\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*</(?:box|bbox)>")
BOX_IN_POINT_TAG = re.compile(r"<point>\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*</point>")
NUMBERS = re.compile(r"-?\d+(?:\.\d+)?")


def parse_action(
    text: str,
    image_size: tuple[int, int],
    metadata: dict[str, object] | None = None,
) -> Action:
    raw = text or ""
    space = CoordinateSpace.from_image(image_size, metadata)
    action_text = _action_text(raw) or raw.strip()
    completion_check = parse_completion_check(_line(COMPLETION_CHECK_LINE, raw))
    thought = _line(THOUGHT_LINE, raw)
    expected = _line(EXPECTED_LINE, raw)
    grounding_text = _line(GROUNDING_LINE, raw)
    grounding = parse_grounding(grounding_text, space)
    grounding["elements"] = parse_elements(_elements_text(raw), space)

    name, args = _call(action_text)
    kind = _kind(name)
    action = Action(
        kind=kind,
        thought=thought,
        grounding=grounding,
        completion_check=completion_check,
        expected=expected,
        raw_text=raw,
        target=str(grounding.get("target") or ""),
    )
    if kind == ActionKind.BATCH:
        actions_text = _batch_call_payload(action_text) or _actions_text(raw)
        action.sub_actions = parse_sub_actions(
            actions_text,
            space,
            raw=raw,
            thought=thought,
            expected=expected,
            completion_check=completion_check,
        )
        return action

    if kind in {ActionKind.CLICK, ActionKind.DOUBLE_CLICK, ActionKind.RIGHT_CLICK, ActionKind.SCROLL}:
        action.point = _point(args.get("point", ""), space, screen=True)
        if kind == ActionKind.CLICK and args.get("key"):
            action.key = str(args["key"])
    if kind == ActionKind.DRAG:
        action.point = _point(args.get("start_point", ""), space, screen=True)
        action.end_point = _point(args.get("end_point", ""), space, screen=True)
    if kind == ActionKind.SCROLL:
        action.direction = str(args.get("direction") or "down")
    if kind == ActionKind.TYPE_TEXT:
        point = grounding.get("point_screen")
        if isinstance(point, Point):
            action.point = point
        action.text = str(args.get("content") or "")
        if "clear_existing" in args:
            action.clear_existing = str(args["clear_existing"]).lower() == "true"
    if kind == ActionKind.HOTKEY:
        action.key = str(args.get("key") or "")
    if kind == ActionKind.FINISHED:
        action.text = str(args.get("content") or "")
    return action


def parse_sub_actions(
    text: str,
    space: CoordinateSpace,
    *,
    raw: str = "",
    thought: str = "",
    expected: str = "",
    completion_check: dict[str, object] | None = None,
) -> list[Action]:
    parsed = _parse_json_value(text)
    if not isinstance(parsed, list):
        return []
    actions: list[Action] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = str(item.get("action") or item.get("kind") or "")
        if not name:
            continue
        kind = _kind(name)
        grounding = _grounding_from_item(item, space)
        action = Action(
            kind=kind,
            target=str(item.get("target") or grounding.get("target") or ""),
            thought=str(item.get("thought") or thought or ""),
            grounding=grounding,
            completion_check=dict(completion_check or {}),
            expected=str(item.get("expected") or expected or ""),
            raw_text=raw,
        )
        if kind in {ActionKind.CLICK, ActionKind.DOUBLE_CLICK, ActionKind.RIGHT_CLICK, ActionKind.SCROLL}:
            action.point = _item_point(item, space)
            if kind == ActionKind.CLICK and item.get("key"):
                action.key = str(item["key"])
        if kind == ActionKind.DRAG:
            action.point = _item_point(item, space, key="start_point")
            action.end_point = _item_point(item, space, key="end_point")
        if kind == ActionKind.SCROLL:
            action.direction = str(item.get("direction") or "down")
        if kind == ActionKind.TYPE_TEXT:
            action.text = str(item.get("content") or item.get("text") or "")
            if "clear_existing" in item:
                action.clear_existing = _as_bool(item.get("clear_existing"))
        if kind == ActionKind.HOTKEY:
            action.key = str(item.get("key") or "")
        if kind == ActionKind.FINISHED:
            action.text = str(item.get("content") or item.get("text") or "")
        actions.append(action)
    return actions


def parse_completion_check(text: str) -> dict[str, object]:
    if not text:
        return {}
    raw = text.strip()
    parsed = _parse_json_value(raw)
    if isinstance(parsed, dict):
        status = str(parsed.get("status") or "uncertain").strip().lower()
        if status not in {"satisfied", "not_satisfied", "uncertain"}:
            status = "uncertain"
        reason = str(parsed.get("reason") or parsed.get("evidence") or raw)
        result: dict[str, object] = {"raw": raw, "status": status, "evidence": reason}
        if "last_action_result" in parsed:
            result["last_action_result"] = str(parsed.get("last_action_result") or "")
        return result
    status = "uncertain"
    lowered = raw.lower()
    if re.search(r"\bsatisfied\b|已完成|完成|满足", lowered):
        status = "satisfied"
    if re.search(r"\bnot[_ -]?satisfied\b|\bunsatisfied\b|未完成|不满足|没有完成", lowered):
        status = "not_satisfied"
    if re.search(r"\buncertain\b|不确定|无法确认", lowered):
        status = "uncertain"
    evidence = raw
    match = re.match(r"([a-zA-Z_ -]+)\s*[-:|，,]\s*(.+)$", raw)
    if match:
        evidence = match.group(2).strip()
    return {"raw": raw, "status": status, "evidence": evidence}


def parse_grounding(text: str, space: CoordinateSpace) -> dict[str, object]:
    if not text:
        return {}
    result: dict[str, object] = {"raw": text}
    for key in ["target", "confidence", "evidence"]:
        match = re.search(rf"{key}='([^']*)'", text)
        if match:
            result[key] = match.group(1)
    point_match = POINT.search(text)
    if point_match:
        x, y = int(point_match.group(1)), int(point_match.group(2))
        result["point_0_1000"] = [x, y]
        result["point_image"] = space.to_image_point(x, y)
        result["point_screen"] = space.to_screen_point(x, y)
    box_match = BOX.search(text) or BOX_IN_POINT_TAG.search(_bbox_value(text))
    if box_match:
        values = tuple(int(box_match.group(i)) for i in range(1, 5))
        result["box_0_1000"] = list(values)
        result["box_image"] = space.to_image_box(values)
        result["box_screen"] = space.to_screen_box(values)
    return result


def parse_elements(text: str, space: CoordinateSpace) -> list[dict[str, object]]:
    if not text:
        return []
    parsed = _parse_elements_json(text)
    if not isinstance(parsed, list):
        return []

    elements: list[dict[str, object]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        element: dict[str, object] = {}
        for key in ["name", "role", "confidence", "evidence"]:
            value = item.get(key)
            if value is not None:
                element[key] = str(value)
        point = _coerce_numbers(item.get("point"), expected=2)
        if point:
            element["point_0_1000"] = point
            element["point_image"] = space.to_image_point(point[0], point[1])
            element["point_screen"] = space.to_screen_point(point[0], point[1])
        bbox = _coerce_numbers(item.get("bbox"), expected=4)
        if bbox:
            values = tuple(bbox)
            element["box_0_1000"] = bbox
            element["box_image"] = space.to_image_box(values)
            element["box_screen"] = space.to_screen_box(values)
        if element:
            elements.append(element)
    return elements


def _line(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    # Fallback: handle markdown heading format (### Thought\nactual content)
    field_name = pattern.pattern.split(r":\s*")[0].lstrip("^").strip()
    heading_match = re.search(
        rf"^#{{1,4}}\s*{field_name}\s*\n+\s*(.+?)$",
        text or "",
        re.IGNORECASE | re.MULTILINE,
    )
    return heading_match.group(1).strip() if heading_match else ""


def _elements_text(text: str) -> str:
    single_line = _line(ELEMENTS_LINE, text)
    if single_line.startswith("[") and single_line.rstrip().endswith("]"):
        return single_line
    match = re.search(
        r"^Elements:\s*(.+?)(?=^Expected:|^Action:|\Z)",
        text or "",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else single_line


def _actions_text(text: str) -> str:
    single_line = _line(ACTIONS_LINE, text)
    if single_line.startswith("[") and single_line.rstrip().endswith("]"):
        return single_line
    match = re.search(
        r"^Actions:\s*(.+?)(?=^Expected:|^Action:|^Elements:|\Z)",
        text or "",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else single_line


def _batch_call_payload(text: str) -> str:
    match = re.match(r"batch\((.*)\)\s*$", (text or "").strip(), re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    payload = match.group(1).strip()
    keyed_match = re.match(r"actions\s*(?:=|:)\s*(\[.*\])\s*$", payload, re.IGNORECASE | re.DOTALL)
    if keyed_match:
        return keyed_match.group(1).strip()
    return payload


def _action_text(text: str) -> str:
    single_line = _line(ACTION_LINE, text)
    if single_line and _looks_complete_call(single_line):
        return single_line
    match = re.search(
        r"^Action:\s*(.+?)(?=^Thought:|^Grounding:|^Expected:|^Elements:|\Z)",
        text or "",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    heading_match = re.search(
        r"^#{1,4}\s*Action\s*\n+\s*(.+?)(?=^#{1,4}\s|\Z)",
        text or "",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if heading_match:
        candidate = heading_match.group(1).strip().split("\n")[0].strip()
        if _looks_complete_call(candidate):
            return candidate
    return single_line


def _looks_complete_call(text: str) -> bool:
    return bool(re.match(r"[a-zA-Z_]+\(.*\)\s*$", text.strip(), re.DOTALL))


def _call(text: str) -> tuple[str, dict[str, str]]:
    match = re.match(r"([a-zA-Z_]+)\((.*)\)\s*$", text.strip(), re.DOTALL)
    if not match:
        raise ValueError(f"Cannot parse action call: {text}")
    name = match.group(1)
    args_text = match.group(2)
    args = _parse_call_args(args_text)
    return name, args


def _parse_call_args(text: str) -> dict[str, str]:
    args: dict[str, str] = {}
    pos = 0
    while pos < len(text):
        match = re.search(r"(\w+)\s*=\s*(['\"])", text[pos:], re.DOTALL)
        if not match:
            break
        key = match.group(1)
        quote = match.group(2)
        value_start = pos + match.end()
        value_end = _quoted_arg_end(text, value_start, quote)
        args[key] = _unescape_arg(text[value_start:value_end])
        pos = value_end + 1
    return args


def _quoted_arg_end(text: str, start: int, quote: str) -> int:
    pos = start
    while pos < len(text):
        if text[pos] != quote or _is_escaped(text, pos):
            pos += 1
            continue
        rest = text[pos + 1 :]
        if re.match(r"\s*(?:\)|,\s*\w+\s*=|\Z)", rest, re.DOTALL):
            return pos
        pos += 1
    return len(text)


def _is_escaped(text: str, pos: int) -> bool:
    count = 0
    index = pos - 1
    while index >= 0 and text[index] == "\\":
        count += 1
        index -= 1
    return count % 2 == 1


def _unescape_arg(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\'", "'")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def _bbox_value(text: str) -> str:
    match = re.search(r"bbox='([^']*)'", text or "")
    return match.group(1) if match else ""


def _parse_elements_json(text: str) -> object:
    return _parse_json_value(text)


def _parse_json_value(text: str) -> object:
    value = text.strip()
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass
    relaxed = value.replace("'", '"')
    relaxed = re.sub(r",\s*([}\]])", r"\1", relaxed)
    try:
        return json.loads(relaxed)
    except json.JSONDecodeError:
        return []


def _grounding_from_item(item: dict[str, object], space: CoordinateSpace) -> dict[str, object]:
    result: dict[str, object] = {}
    target = item.get("target") or item.get("name")
    if target is not None:
        result["target"] = str(target)
    for key in ["confidence", "evidence"]:
        value = item.get(key)
        if value is not None:
            result[key] = str(value)
    point = _coerce_numbers(item.get("point"), expected=2)
    if point:
        result["point_0_1000"] = point
        result["point_image"] = space.to_image_point(point[0], point[1])
        result["point_screen"] = space.to_screen_point(point[0], point[1])
    bbox = _coerce_numbers(item.get("bbox"), expected=4)
    if bbox:
        values = tuple(bbox)
        result["box_0_1000"] = bbox
        result["box_image"] = space.to_image_box(values)
        result["box_screen"] = space.to_screen_box(values)
    return result


def _item_point(item: dict[str, object], space: CoordinateSpace, *, key: str = "point") -> Point | None:
    value = item.get(key)
    numbers = _coerce_numbers(value, expected=2)
    if numbers:
        return space.to_screen_point(numbers[0], numbers[1])
    if isinstance(value, str):
        return _point(value, space, screen=True)
    return None


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _coerce_numbers(value: object, *, expected: int) -> list[int]:
    if not isinstance(value, (list, tuple)) or len(value) != expected:
        return []
    try:
        return [int(round(float(item))) for item in value]
    except (TypeError, ValueError):
        return []


def _kind(name: str) -> ActionKind:
    aliases = {
        "click": ActionKind.CLICK,
        "left_double": ActionKind.DOUBLE_CLICK,
        "double_click": ActionKind.DOUBLE_CLICK,
        "right_single": ActionKind.RIGHT_CLICK,
        "right_click": ActionKind.RIGHT_CLICK,
        "drag": ActionKind.DRAG,
        "scroll": ActionKind.SCROLL,
        "type": ActionKind.TYPE_TEXT,
        "type_text": ActionKind.TYPE_TEXT,
        "hotkey": ActionKind.HOTKEY,
        "wait": ActionKind.WAIT,
        "finished": ActionKind.FINISHED,
        "batch": ActionKind.BATCH,
    }
    try:
        return aliases[name.strip().lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported action: {name}") from exc


def _point(value: str, space: CoordinateSpace, *, screen: bool) -> Point | None:
    match = POINT.search(value)
    if not match:
        return None
    x, y = int(match.group(1)), int(match.group(2))
    if screen:
        return space.to_screen_point(x, y)
    return space.to_image_point(x, y)


def _scale_point(x: int, y: int, image_size: tuple[int, int]) -> Point:
    width, height = image_size
    return Point(round(x / 1000 * width), round(y / 1000 * height))


def _scale_box(values: tuple[int, int, int, int], image_size: tuple[int, int]) -> Box:
    p1 = _scale_point(values[0], values[1], image_size)
    p2 = _scale_point(values[2], values[3], image_size)
    return Box(p1.x, p1.y, p2.x, p2.y)
