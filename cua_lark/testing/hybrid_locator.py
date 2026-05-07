from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from cua_lark.adapters.accessibility import AccessibilityCandidate, collect_accessibility_candidates
from cua_lark.domain.models import Action, ActionKind, Box, Point


@dataclass(frozen=True)
class HybridLocatorResult:
    matched: bool
    reason: str
    original_point: Point | None = None
    point: Point | None = None
    candidate: AccessibilityCandidate | None = None
    score: float = 0.0
    semantic_score: float = 0.0
    spatial_score: float = 0.0
    candidate_count: int = 0

    def as_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "matched": self.matched,
            "reason": self.reason,
            "score": round(self.score, 3),
            "semantic_score": round(self.semantic_score, 3),
            "spatial_score": round(self.spatial_score, 3),
            "candidate_count": self.candidate_count,
        }
        if self.original_point:
            data["original_point_screen"] = [self.original_point.x, self.original_point.y]
        if self.point:
            data["point_screen"] = [self.point.x, self.point.y]
        if self.candidate:
            data["candidate"] = {
                "role": self.candidate.role,
                "label": self.candidate.label,
                "enabled": self.candidate.enabled,
                "box_screen": _box_list(self.candidate.box_screen),
            }
        return data


def apply_hybrid_locator(
    action: Action,
    *,
    app_names: list[str],
    metadata: dict[str, object],
) -> HybridLocatorResult:
    if action.kind not in {ActionKind.CLICK, ActionKind.DOUBLE_CLICK, ActionKind.RIGHT_CLICK}:
        return HybridLocatorResult(False, "not_click_action")
    candidates = collect_accessibility_candidates(app_names)
    result = locate_action_with_candidates(action, candidates, metadata=metadata)
    action.grounding["hybrid_locator"] = result.as_dict()
    if result.matched and result.point:
        action.point = result.point
        action.grounding_check = {
            "triggered": False,
            "mode": "hybrid",
            "reason": "accessibility_grounded",
            "hybrid_locator": result.as_dict(),
        }
    return result


def locate_action_with_candidates(
    action: Action,
    candidates: list[AccessibilityCandidate],
    *,
    metadata: dict[str, object] | None = None,
) -> HybridLocatorResult:
    if not candidates:
        return HybridLocatorResult(False, "no_accessibility_candidates")
    target_text = _target_text(action)
    if not target_text:
        return HybridLocatorResult(False, "empty_target", candidate_count=len(candidates))
    scored: list[HybridLocatorResult] = []
    for candidate in candidates:
        if candidate.enabled is False or candidate.box_screen is None:
            continue
        if not _inside_capture(candidate.box_screen, metadata or {}):
            continue
        semantic = _semantic_score(target_text, candidate)
        spatial = _spatial_score(action, candidate)
        score = semantic * 0.68 + spatial * 0.32
        if semantic <= 0 and spatial < 0.95:
            continue
        scored.append(
            HybridLocatorResult(
                matched=True,
                reason="candidate",
                original_point=action.point,
                point=candidate.box_screen.center,
                candidate=candidate,
                score=score,
                semantic_score=semantic,
                spatial_score=spatial,
                candidate_count=len(candidates),
            )
        )
    if not scored:
        return HybridLocatorResult(False, "no_matching_candidate", candidate_count=len(candidates))
    scored.sort(key=lambda item: item.score, reverse=True)
    best = scored[0]
    second = scored[1] if len(scored) > 1 else None
    if best.semantic_score >= 0.55 and best.spatial_score >= 0.25 and best.score >= 0.50:
        if second and second.score > best.score - 0.08:
            return HybridLocatorResult(
                False,
                "ambiguous_accessibility_candidates",
                original_point=action.point,
                score=best.score,
                semantic_score=best.semantic_score,
                spatial_score=best.spatial_score,
                candidate_count=len(candidates),
            )
        return HybridLocatorResult(
            True,
            "accessibility_semantic_spatial_match",
            original_point=action.point,
            point=best.point,
            candidate=best.candidate,
            score=best.score,
            semantic_score=best.semantic_score,
            spatial_score=best.spatial_score,
            candidate_count=len(candidates),
        )
    return HybridLocatorResult(
        False,
        "best_candidate_below_threshold",
        original_point=action.point,
        score=best.score,
        semantic_score=best.semantic_score,
        spatial_score=best.spatial_score,
        candidate_count=len(candidates),
    )


def _target_text(action: Action) -> str:
    return " ".join(
        str(item or "")
        for item in [
            action.target,
            action.grounding.get("target"),
            action.grounding.get("evidence"),
        ]
    ).lower()


def _semantic_score(text: str, candidate: AccessibilityCandidate) -> float:
    label = candidate.label.lower()
    if not label:
        return 0.0
    aliases = {
        "emoji": ["emoji", "表情", "smiley", "emotion"],
        "表情": ["emoji", "表情", "smiley", "emotion"],
        "send": ["send", "发送", "紙飛機", "纸飞机"],
        "发送": ["send", "发送", "紙飛機", "纸飞机"],
        "mention": ["mention", "@", "提及"],
        "提及": ["mention", "@", "提及"],
        "search": ["search", "搜索"],
        "搜索": ["search", "搜索"],
        "input": ["input", "输入", "composer", "文本", "消息"],
        "输入": ["input", "输入", "composer", "文本", "消息"],
    }
    score = 0.0
    for token in _tokens(text):
        variants = aliases.get(token, [token])
        if any(variant and variant in label for variant in variants):
            score += 1.0
    role = candidate.role.lower()
    if "button" in role and any(term in text for term in ["button", "按钮", "emoji", "表情", "send", "发送", "@"]):
        score += 0.35
    if any(term in role for term in ["textfield", "textarea", "text area"]) and any(
        term in text for term in ["input", "输入", "composer", "消息输入框"]
    ):
        score += 0.45
    return min(1.0, score / 1.6)


def _tokens(text: str) -> list[str]:
    raw = (
        text.replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .replace("'", " ")
        .replace('"', " ")
    )
    tokens = [item.strip().lower() for item in raw.split() if item.strip()]
    for term in ["表情", "发送", "提及", "搜索", "输入", "按钮", "@", "emoji", "send", "mention", "input", "search"]:
        if term in text:
            tokens.append(term)
    return tokens


def _spatial_score(action: Action, candidate: AccessibilityCandidate) -> float:
    box = candidate.box_screen
    if box is None:
        return 0.0
    action_box = action.grounding.get("box_screen")
    if isinstance(action_box, Box):
        overlap = _iou(action_box, box)
        if overlap > 0:
            return min(1.0, 0.35 + overlap)
    if action.point:
        distance = _distance(action.point, box.center)
        diagonal = max(1.0, math.hypot(abs(box.x2 - box.x1), abs(box.y2 - box.y1)))
        if _point_in_box(action.point, box):
            return 1.0
        return max(0.0, 1.0 - distance / max(80.0, diagonal * 2.0))
    return 0.0


def _inside_capture(box: Box, metadata: dict[str, object]) -> bool:
    bounds = metadata.get("window_bounds")
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
        return True
    x, y, width, height = [int(item) for item in bounds]
    capture = Box(x, y, x + width, y + height)
    return _iou(box, capture) > 0 or _point_in_box(box.center, capture)


def _iou(left: Box, right: Box) -> float:
    x1 = max(min(left.x1, left.x2), min(right.x1, right.x2))
    y1 = max(min(left.y1, left.y2), min(right.y1, right.y2))
    x2 = min(max(left.x1, left.x2), max(right.x1, right.x2))
    y2 = min(max(left.y1, left.y2), max(right.y1, right.y2))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    intersection = (x2 - x1) * (y2 - y1)
    left_area = abs(left.x2 - left.x1) * abs(left.y2 - left.y1)
    right_area = abs(right.x2 - right.x1) * abs(right.y2 - right.y1)
    union = max(1, left_area + right_area - intersection)
    return intersection / union


def _distance(left: Point, right: Point) -> float:
    return math.hypot(left.x - right.x, left.y - right.y)


def _point_in_box(point: Point, box: Box) -> bool:
    return min(box.x1, box.x2) <= point.x <= max(box.x1, box.x2) and min(box.y1, box.y2) <= point.y <= max(box.y1, box.y2)


def _box_list(box: Box | None) -> list[int]:
    if not box:
        return []
    return [box.x1, box.y1, box.x2, box.y2]
