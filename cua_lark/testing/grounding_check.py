from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw

from cua_lark.domain.coordinates import CoordinateSpace
from cua_lark.domain.models import Action, ActionKind, Box, Point, TestCase
from cua_lark.testing.observation import is_input_focus_target


CHECKABLE_ACTIONS = {ActionKind.CLICK, ActionKind.DOUBLE_CLICK, ActionKind.RIGHT_CLICK}
POINT = re.compile(r"<point>\s*(\d+)\s+(\d+)\s*</point>")
HIGH_RISK_TERMS = {
    "@",
    "mention",
    "提及",
    "toolbar",
    "工具栏",
    "emoji",
    "表情",
    "plus",
    "加号",
    "screenshot",
    "截图",
    "popup",
    "pop-up",
    "picker",
    "弹窗",
    "菜单",
    "menu",
    "option",
    "选项",
}
SMALL_BOX_MAX_SIZE = 35
LOW_CONFIDENCE_THRESHOLD = 0.85


@dataclass(frozen=True)
class GroundingCheck:
    annotated_image: Image.Image
    prompt: str


def needs_grounding_check(action: Action) -> bool:
    return action.kind in CHECKABLE_ACTIONS and action.point is not None


def grounding_check_risk(action: Action, *, mode: str = "high-risk") -> dict[str, Any]:
    if not needs_grounding_check(action):
        return {"triggered": False, "mode": mode, "reason": "not_click_action"}
    if mode == "all":
        return {"triggered": True, "mode": mode, "reason": "all_clicks"}
    if mode != "high-risk":
        return {"triggered": False, "mode": mode, "reason": "unknown_mode"}

    box = _normalized_box(action)
    point = _normalized_point(action)
    confidence = _float(action.grounding.get("confidence"))
    geometry = _geometry_summary(box, point, confidence)

    if box and point and not _point_in_box(point, box):
        return {
            "triggered": True,
            "mode": mode,
            "reason": "point_outside_grounding_box",
            **geometry,
        }

    if _is_self_consistent_text_input(action, box, point, confidence):
        return {
            "triggered": False,
            "mode": mode,
            "reason": "text_input_focus_target",
            **geometry,
        }

    if box:
        width, height = _box_size(box)
        if width <= SMALL_BOX_MAX_SIZE or height <= SMALL_BOX_MAX_SIZE:
            return {
                "triggered": True,
                "mode": mode,
                "reason": "small_grounding_box",
                **geometry,
            }

    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        return {
            "triggered": True,
            "mode": mode,
            "reason": "low_grounding_confidence",
            **geometry,
        }

    text = " ".join([action.target, action.thought, str(action.grounding.get("evidence") or "")]).lower()
    matched = sorted(term for term in HIGH_RISK_TERMS if term.lower() in text)
    if matched:
        return {
            "triggered": True,
            "mode": mode,
            "reason": "matched_high_risk_terms",
            "terms": matched,
            **geometry,
        }

    return {"triggered": False, "mode": mode, "reason": "self_consistent_large_target", **geometry}


def build_grounding_check(action: Action, image: Image.Image, case: TestCase) -> GroundingCheck:
    annotated = image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    point = _image_point(action, image)
    box = _image_box(action)
    if box:
        draw.rectangle([box.x1, box.y1, box.x2, box.y2], outline="yellow", width=4)
    if point:
        r = 14
        draw.ellipse([point.x - r, point.y - r, point.x + r, point.y + r], outline="red", width=5)
        draw.line([point.x - 24, point.y, point.x + 24, point.y], fill="red", width=3)
        draw.line([point.x, point.y - 24, point.x, point.y + 24], fill="red", width=3)

    prompt = "\n".join(
        [
            "You are checking a proposed GUI click before it is executed.",
            "The screenshot has a red crosshair marking the proposed click point.",
            "A yellow rectangle may mark the model's claimed target bounding box.",
            "",
            f"User task: {case.instruction}",
            f"Action type: {action.kind.value}",
            f"Target object: {action.target or 'unknown'}",
            f"Model thought: {action.thought}",
            "",
            "Decide whether the red crosshair is on the intended target object.",
            "If it is correct, return PASS and repeat the same point.",
            "If it is wrong or ambiguous, return CORRECTED and provide the better click point.",
            "Use 0-1000 coordinates relative to the full screenshot.",
            "",
            "Return exactly this format:",
            "Verdict: PASS|CORRECTED|UNCERTAIN",
            "CorrectedPoint: <point>x y</point>",
            "Reason: short reason",
        ]
    )
    return GroundingCheck(annotated_image=annotated, prompt=prompt)


def apply_grounding_check_response(
    action: Action,
    raw: str,
    image_size: tuple[int, int],
    metadata: dict[str, Any],
) -> None:
    verdict = _line("Verdict", raw).upper()
    corrected = POINT.search(raw or "")
    result: dict[str, Any] = {
        "raw": raw,
        "verdict": verdict or "UNPARSED",
        "reason": _line("Reason", raw),
        "changed_point": False,
    }
    if corrected and verdict in {"CORRECTED", "UNCERTAIN"}:
        x, y = int(corrected.group(1)), int(corrected.group(2))
        space = CoordinateSpace.from_image(image_size, metadata)
        action.point = space.to_screen_point(x, y)
        result["changed_point"] = True
        result["corrected_point_0_1000"] = [x, y]
        result["corrected_point_image"] = space.to_image_point(x, y)
        result["corrected_point_screen"] = action.point
    action.grounding_check = result


def _line(name: str, text: str) -> str:
    match = re.search(rf"^{name}:\s*(.+?)\s*$", text or "", re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _image_point(action: Action, image: Image.Image) -> Point | None:
    value = action.grounding.get("point_image")
    if isinstance(value, Point):
        return value
    if action.point is None:
        return None
    offset = image.info.get("screen_offset") or (0, 0)
    scale = image.info.get("screen_scale") or (1.0, 1.0)
    try:
        return Point(
            round((action.point.x - int(offset[0])) / float(scale[0])),
            round((action.point.y - int(offset[1])) / float(scale[1])),
        )
    except Exception:
        return None


def _image_box(action: Action) -> Box | None:
    value = action.grounding.get("box_image")
    return value if isinstance(value, Box) else None


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalized_box(action: Action) -> list[int] | None:
    box = action.grounding.get("box_0_1000")
    if isinstance(box, list) and len(box) == 4:
        try:
            values = [int(item) for item in box]
            return [min(values[0], values[2]), min(values[1], values[3]), max(values[0], values[2]), max(values[1], values[3])]
        except (TypeError, ValueError):
            return None
    return None


def _normalized_point(action: Action) -> list[int] | None:
    point = action.grounding.get("point_0_1000")
    if isinstance(point, list) and len(point) == 2:
        try:
            return [int(point[0]), int(point[1])]
        except (TypeError, ValueError):
            return None
    return None


def _point_in_box(point: list[int], box: list[int]) -> bool:
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def _box_size(box: list[int]) -> tuple[int, int]:
    return abs(box[2] - box[0]), abs(box[3] - box[1])


def _is_self_consistent_text_input(
    action: Action,
    box: list[int] | None,
    point: list[int] | None,
    confidence: float | None,
) -> bool:
    if not is_input_focus_target(action):
        return False
    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        return False
    if not box or not point or not _point_in_box(point, box):
        return action.point is not None and not box
    width, height = _box_size(box)
    return width >= 120 and height >= 18


def _geometry_summary(box: list[int] | None, point: list[int] | None, confidence: float | None) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if box:
        summary["box_0_1000"] = box
        summary["box_size_0_1000"] = list(_box_size(box))
    if point:
        summary["point_0_1000"] = point
    if box and point:
        summary["point_inside_box"] = _point_in_box(point, box)
    if confidence is not None:
        summary["confidence"] = confidence
    return summary
