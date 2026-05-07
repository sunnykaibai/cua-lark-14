from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cua_lark.domain.models import Box, Point


@dataclass(frozen=True)
class AccessibilityCandidate:
    role: str = ""
    title: str = ""
    description: str = ""
    value: str = ""
    identifier: str = ""
    enabled: bool | None = None
    box_screen: Box | None = None

    @property
    def label(self) -> str:
        return " ".join(
            item
            for item in [self.title, self.description, self.value, self.identifier, self.role]
            if item
        ).strip()


def collect_accessibility_candidates(
    app_names: list[str],
    *,
    max_nodes: int = 900,
) -> list[AccessibilityCandidate]:
    pid = _frontmost_matching_pid(app_names)
    if pid is None:
        return []
    try:
        from ApplicationServices import AXUIElementCreateApplication
    except Exception:
        return []

    app = AXUIElementCreateApplication(pid)
    windows = _copy_attr(app, "AXWindows")
    roots = _as_list(windows) or [app]
    candidates: list[AccessibilityCandidate] = []
    queue = list(roots)
    seen: set[int] = set()
    while queue and len(seen) < max_nodes:
        element = queue.pop(0)
        marker = id(element)
        if marker in seen:
            continue
        seen.add(marker)
        candidate = _candidate_from_element(element)
        if candidate:
            candidates.append(candidate)
        for attr in ["AXChildren", "AXVisibleChildren", "AXRows", "AXColumns", "AXContents"]:
            children = _copy_attr(element, attr)
            queue.extend(_as_list(children))
    return candidates


def _candidate_from_element(element: object) -> AccessibilityCandidate | None:
    role = _string_attr(element, "AXRole")
    title = _string_attr(element, "AXTitle")
    description = _string_attr(element, "AXDescription")
    value = _string_attr(element, "AXValue")
    identifier = _string_attr(element, "AXIdentifier")
    enabled_value = _copy_attr(element, "AXEnabled")
    enabled = bool(enabled_value) if enabled_value is not None else None
    frame = _rect_attr(element, "AXFrame")
    position = _point_attr(element, "AXPosition")
    size = _size_attr(element, "AXSize")
    box = None
    if frame:
        box = frame
    elif position and size and size.x > 0 and size.y > 0:
        box = Box(position.x, position.y, position.x + size.x, position.y + size.y)
    if not any([role, title, description, value, identifier, box]):
        return None
    return AccessibilityCandidate(
        role=role,
        title=title,
        description=description,
        value=value,
        identifier=identifier,
        enabled=enabled,
        box_screen=box,
    )


def _frontmost_matching_pid(app_names: list[str]) -> int | None:
    try:
        import Quartz
    except Exception:
        return None
    normalized = {name.lower() for name in app_names}
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    candidates: list[tuple[int, int]] = []
    for window in windows:
        owner = str(window.get("kCGWindowOwnerName") or "")
        if owner.lower() not in normalized or window.get("kCGWindowLayer") != 0:
            continue
        bounds = window.get("kCGWindowBounds") or {}
        area = int(bounds.get("Width", 0)) * int(bounds.get("Height", 0))
        pid = window.get("kCGWindowOwnerPID")
        if area > 0 and pid:
            candidates.append((area, int(pid)))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _copy_attr(element: object, attr: str) -> Any:
    try:
        from ApplicationServices import AXUIElementCopyAttributeValue

        result = AXUIElementCopyAttributeValue(element, attr, None)
        if isinstance(result, tuple) and len(result) >= 2:
            err, value = result[0], result[1]
            return value if err == 0 else None
        return result
    except Exception:
        return None


def _as_list(value: object) -> list[object]:
    if value is None or isinstance(value, (str, bytes)):
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if hasattr(value, "__iter__"):
        try:
            return list(value)  # type: ignore[arg-type]
        except Exception:
            return []
    return []


def _string_attr(element: object, attr: str) -> str:
    value = _copy_attr(element, attr)
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return ""


def _point_attr(element: object, attr: str) -> Point | None:
    return _point_like(_copy_attr(element, attr))


def _size_attr(element: object, attr: str) -> Point | None:
    return _point_like(_copy_attr(element, attr))


def _rect_attr(element: object, attr: str) -> Box | None:
    value = _copy_attr(element, attr)
    if value is None:
        return None
    for names in [("x", "y", "width", "height"), ("origin", "size")]:
        try:
            if len(names) == 4 and all(hasattr(value, name) for name in names):
                x = round(float(getattr(value, "x")))
                y = round(float(getattr(value, "y")))
                width = round(float(getattr(value, "width")))
                height = round(float(getattr(value, "height")))
                return Box(x, y, x + width, y + height)
            if len(names) == 2 and hasattr(value, "origin") and hasattr(value, "size"):
                origin = getattr(value, "origin")
                size = getattr(value, "size")
                x = round(float(getattr(origin, "x")))
                y = round(float(getattr(origin, "y")))
                width = round(float(getattr(size, "width")))
                height = round(float(getattr(size, "height")))
                return Box(x, y, x + width, y + height)
        except Exception:
            pass
    try:
        import ApplicationServices as AS

        converted = AS.AXValueGetValue(value, AS.kAXValueCGRectType, None)
        if isinstance(converted, tuple) and len(converted) == 2:
            converted = converted[1] if converted[0] else None
        if hasattr(converted, "origin") and hasattr(converted, "size"):
            origin = getattr(converted, "origin")
            size = getattr(converted, "size")
            x = round(float(getattr(origin, "x")))
            y = round(float(getattr(origin, "y")))
            width = round(float(getattr(size, "width")))
            height = round(float(getattr(size, "height")))
            return Box(x, y, x + width, y + height)
    except Exception:
        return None
    return None


def _point_like(value: object) -> Point | None:
    if value is None:
        return None
    for x_name, y_name in [("x", "y"), ("width", "height")]:
        if hasattr(value, x_name) and hasattr(value, y_name):
            try:
                return Point(round(float(getattr(value, x_name))), round(float(getattr(value, y_name))))
            except Exception:
                return None
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        try:
            return Point(round(float(value[0])), round(float(value[1])))
        except Exception:
            return None
    try:
        import ApplicationServices as AS

        for value_type in [AS.kAXValueCGPointType, AS.kAXValueCGSizeType]:
            try:
                converted = AS.AXValueGetValue(value, value_type, None)
                if isinstance(converted, tuple) and len(converted) == 2:
                    converted = converted[1] if converted[0] else None
                if isinstance(converted, tuple) and len(converted) >= 2:
                    return Point(round(float(converted[0])), round(float(converted[1])))
                if hasattr(converted, "x") and hasattr(converted, "y"):
                    return Point(round(float(getattr(converted, "x"))), round(float(getattr(converted, "y"))))
                if hasattr(converted, "width") and hasattr(converted, "height"):
                    return Point(round(float(getattr(converted, "width"))), round(float(getattr(converted, "height"))))
            except Exception:
                continue
    except Exception:
        return None
    return None
