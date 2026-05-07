from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cua_lark.domain.models import Box, Point


@dataclass(frozen=True)
class CoordinateSpace:
    image_width: int
    image_height: int
    origin_x: int = 0
    origin_y: int = 0
    model_scale: int = 1000
    screen_scale_x: float = 1.0
    screen_scale_y: float = 1.0

    @classmethod
    def from_image(cls, image_size: tuple[int, int], metadata: dict[str, Any] | None = None) -> "CoordinateSpace":
        metadata = metadata or {}
        offset = metadata.get("screen_offset") or metadata.get("offset") or (0, 0)
        scale = metadata.get("screen_scale") or metadata.get("scale") or (1.0, 1.0)
        return cls(
            image_width=int(image_size[0]),
            image_height=int(image_size[1]),
            origin_x=_safe_int(offset, 0, 0),
            origin_y=_safe_int(offset, 1, 0),
            screen_scale_x=_safe_float(scale, 0, 1.0),
            screen_scale_y=_safe_float(scale, 1, 1.0),
        )

    def to_image_point(self, x: int | float, y: int | float) -> Point:
        return Point(
            round(float(x) / self.model_scale * self.image_width),
            round(float(y) / self.model_scale * self.image_height),
        )

    def to_screen_point(self, x: int | float, y: int | float) -> Point:
        image_point = self.to_image_point(x, y)
        return Point(
            round(image_point.x * self.screen_scale_x) + self.origin_x,
            round(image_point.y * self.screen_scale_y) + self.origin_y,
        )

    def to_image_box(self, values: tuple[int, int, int, int]) -> Box:
        p1 = self.to_image_point(values[0], values[1])
        p2 = self.to_image_point(values[2], values[3])
        return Box(p1.x, p1.y, p2.x, p2.y)

    def to_screen_box(self, values: tuple[int, int, int, int]) -> Box:
        p1 = self.to_screen_point(values[0], values[1])
        p2 = self.to_screen_point(values[2], values[3])
        return Box(p1.x, p1.y, p2.x, p2.y)


def _safe_int(value: Any, index: int, default: int) -> int:
    try:
        return int(value[index])
    except (TypeError, ValueError, IndexError):
        return default


def _safe_float(value: Any, index: int, default: float) -> float:
    try:
        return float(value[index])
    except (TypeError, ValueError, IndexError):
        return default
