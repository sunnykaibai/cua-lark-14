from __future__ import annotations

import time
from typing import Protocol

from cua_lark.domain.models import Action, ActionKind, Point
from cua_lark.runtime.config import Settings


class Gui(Protocol):
    def execute(self, action: Action) -> None:
        ...


class PyAutoGui:
    def __init__(self, settings: Settings):
        import pyautogui

        self.pyautogui = pyautogui
        self.delay = float(settings.executor.get("operation_delay", 0.6))
        self.move_duration = float(settings.executor.get("mouse_move_duration", 0.15))
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05

    def execute(self, action: Action) -> None:
        kind = action.kind
        if kind == ActionKind.CLICK:
            self._click(action.point, modifiers=_parse_click_modifiers(action.key))
        elif kind == ActionKind.DOUBLE_CLICK:
            self._click(action.point, clicks=2)
        elif kind == ActionKind.RIGHT_CLICK:
            self._click(action.point, button="right")
        elif kind == ActionKind.DRAG:
            self._drag(action.point, action.end_point)
        elif kind == ActionKind.SCROLL:
            self._move(action.point)
            self.pyautogui.scroll(5 if action.direction == "up" else -5)
        elif kind == ActionKind.TYPE_TEXT:
            if action.clear_existing:
                self._hotkey(["command", "a"])
                self.pyautogui.press("backspace")
            self._paste_text(action.text)
        elif kind == ActionKind.HOTKEY:
            keys = [item for item in action.key.replace("+", " ").split() if item]
            self._hotkey(keys)
        elif kind == ActionKind.WAIT:
            time.sleep(self.delay)
            return
        elif kind == ActionKind.FINISHED:
            return
        else:
            raise ValueError(f"Unsupported action kind: {kind}")
        time.sleep(self.delay)

    def _move(self, point: Point | None) -> None:
        if point is None:
            return
        self.pyautogui.moveTo(point.x, point.y, duration=self.move_duration)

    def _click(self, point: Point | None, button: str = "left", clicks: int = 1, modifiers: list[str] | None = None) -> None:
        if point is None:
            raise ValueError("Point is required for click action")
        self._move(point)
        if modifiers:
            for mod in modifiers:
                self.pyautogui.keyDown(mod)
            time.sleep(0.05)
        self.pyautogui.click(button=button, clicks=clicks)
        if modifiers:
            time.sleep(0.05)
            for mod in reversed(modifiers):
                self.pyautogui.keyUp(mod)

    def _drag(self, start: Point | None, end: Point | None) -> None:
        if start is None or end is None:
            raise ValueError("Start and end points are required for drag action")
        self._move(start)
        self.pyautogui.dragTo(end.x, end.y, duration=max(self.move_duration, 0.2), button="left")

    def _paste_text(self, text: str) -> None:
        import pyperclip

        pyperclip.copy(text)
        self._hotkey(["command", "v"])

    def _hotkey(self, keys: list[str]) -> None:
        normalized = [_normalize_key(key) for key in keys if key]
        if not normalized:
            return
        if len(normalized) == 1:
            self.pyautogui.press(normalized[0])
            return
        pressed: list[str] = []
        try:
            for key in normalized:
                self.pyautogui.keyDown(key)
                pressed.append(key)
                time.sleep(0.03)
            time.sleep(0.05)
        finally:
            for key in reversed(pressed):
                self.pyautogui.keyUp(key)
                time.sleep(0.02)


class DryRunGui:
    def __init__(self) -> None:
        self.actions: list[Action] = []

    def execute(self, action: Action) -> None:
        self.actions.append(action)


def _normalize_key(key: str) -> str:
    aliases = {
        "cmd": "command",
        "meta": "command",
        "return": "enter",
        "escape": "esc",
    }
    return aliases.get(key.strip().lower(), key.strip().lower())


def _parse_click_modifiers(key: str) -> list[str] | None:
    """Extract modifier keys from click action's key field (e.g. 'shift')."""
    if not key:
        return None
    modifiers = [_normalize_key(k) for k in key.replace("+", " ").split() if k.strip()]
    return modifiers if modifiers else None
