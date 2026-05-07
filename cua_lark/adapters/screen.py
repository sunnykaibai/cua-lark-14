from __future__ import annotations

import platform
import subprocess
import time
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageChops, ImageDraw, ImageGrab, ImageStat

from cua_lark.domain.models import Box, Point


class Screen(Protocol):
    def capture(self) -> Image.Image:
        ...


class PyAutoGuiScreen:
    def __init__(
        self,
        prefer_app_window: bool = True,
        app_names: list[str] | None = None,
        browser_app_names: list[str] | None = None,
        browser_title_keywords: list[str] | None = None,
        prefer_browser_docs: bool = False,
        require_app_window: bool = False,
        app_recovery_names: list[str] | None = None,
        recovery_attempts: int = 2,
    ):
        self.prefer_app_window = prefer_app_window
        self.app_names = app_names or ["飞书", "Feishu", "Lark"]
        self.browser_app_names = browser_app_names or ["Safari", "Google Chrome", "Chrome", "Arc"]
        self.browser_title_keywords = browser_title_keywords or ["feishu.cn", "larksuite.com", "飞书云文档", "未命名文档"]
        self.prefer_browser_docs = prefer_browser_docs
        self.require_app_window = require_app_window
        self.app_recovery_names = app_recovery_names or ["飞书", "Feishu", "Lark", "Safari", "Google Chrome"]
        self.recovery_attempts = max(0, recovery_attempts)
        self._last_app_owner = ""
        self._browser_handoff_captures = 0
        self._capture_role = ""
        self._suppress_browser_precheck = False

    def arm_browser_handoff(self, captures: int = 3) -> None:
        """Temporarily follow a browser window after an app action opens a Docs page there."""
        self._browser_handoff_captures = max(self._browser_handoff_captures, captures)
        self._suppress_browser_precheck = False

    def suppress_browser_precheck(self) -> None:
        """Skip browser precheck until an explicit browser handoff is armed."""
        self._suppress_browser_precheck = True

    def reset_transient_capture_state(self) -> None:
        self._browser_handoff_captures = 0
        self._capture_role = ""
        self._suppress_browser_precheck = False

    def capture(self) -> Image.Image:
        if self.prefer_app_window:
            self._capture_role = ""
            bounds = self._find_or_recover_window()
            if bounds:
                x, y, width, height, owner = bounds
                self._last_app_owner = owner
                # Ensure the target window is frontmost before grabbing pixels.
                self._activate_owner_if_needed(owner)
                try:
                    image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
                except Exception:
                    image = ImageGrab.grab()
                    attach_capture_metadata(image, _full_screen_region(image), "full_screen_fallback", "")
                    return image
                attach_capture_metadata(image, (x, y, width, height), "app_window", owner)
                image.info["capture_role"] = self._capture_role
                if dismiss_macos_screenshot_overlay(image):
                    image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
                    attach_capture_metadata(image, (x, y, width, height), "app_window", owner)
                    image.info["capture_role"] = self._capture_role
                return image
            if self.require_app_window:
                raise RuntimeError(
                    "No matching Feishu/Docs app window was found after environment recovery; refusing full-screen fallback for this run."
                )

        image = ImageGrab.grab()
        attach_capture_metadata(image, _full_screen_region(image), "full_screen", "")
        return image

    def _find_or_recover_window(self) -> tuple[int, int, int, int, str] | None:
        handoff_browser = self._browser_handoff_window_bounds()
        if handoff_browser:
            self._capture_role = "browser_handoff"
            return handoff_browser

        sticky_browser = self._sticky_browser_window_bounds()
        if sticky_browser:
            self._capture_role = "sticky_browser"
            return sticky_browser

        browser_precheck = self._frontmost_browser_docs_precheck_bounds()
        if browser_precheck:
            self._capture_role = "browser_precheck"
            return browser_precheck

        bounds = find_preferred_window_bounds(
            self.app_names,
            browser_app_names=self.browser_app_names,
            browser_title_keywords=self.browser_title_keywords,
            prefer_browser_docs=self.prefer_browser_docs,
            allow_browser_fallback=self.prefer_browser_docs,
        )
        if bounds:
            self._capture_role = "preferred_app"
            return bounds

        recovery_names = self.app_recovery_names
        if not self.prefer_browser_docs:
            recovery_names = [name for name in self.app_recovery_names if not self._owner_is_browser(name)]

        for _ in range(self.recovery_attempts):
            recovered_bounds = recover_preferred_window_bounds(
                recovery_names,
                self.app_names,
                browser_app_names=self.browser_app_names,
                browser_title_keywords=self.browser_title_keywords,
                prefer_browser_docs=self.prefer_browser_docs,
                allow_browser_fallback=self.prefer_browser_docs,
            )
            if recovered_bounds:
                self._capture_role = "recovered_app"
                return recovered_bounds
            if recover_visible_app_window(recovery_names):
                time.sleep(0.8)
            bounds = find_preferred_window_bounds(
                self.app_names,
                browser_app_names=self.browser_app_names,
                browser_title_keywords=self.browser_title_keywords,
                prefer_browser_docs=self.prefer_browser_docs,
                allow_browser_fallback=self.prefer_browser_docs,
            )
            if bounds:
                self._capture_role = "preferred_app_after_recovery"
                return bounds
        if not self.require_app_window:
            fallback_bounds = find_preferred_window_bounds(
                self.app_names,
                browser_app_names=self.browser_app_names,
                browser_title_keywords=self.browser_title_keywords,
                prefer_browser_docs=self.prefer_browser_docs,
                allow_browser_fallback=True,
            )
            if fallback_bounds:
                self._capture_role = "fallback"
                return fallback_bounds
            if self.prefer_browser_docs:
                browser_fallback = find_browser_host_window_bounds(self.browser_app_names)
                if browser_fallback:
                    self._capture_role = "browser_fallback"
                    return browser_fallback
        return None

    def _activate_owner_if_needed(self, owner: str) -> None:
        """Activate the owner app so its window is frontmost before pixel grab."""
        if not owner or platform.system() != "Darwin":
            return
        try:
            from AppKit import NSWorkspace
            frontmost = NSWorkspace.sharedWorkspace().frontmostApplication().localizedName()
            if frontmost and frontmost.lower() == owner.lower():
                return
            # Use NSRunningApplication for reliable activation (works with localized names).
            target_names = {owner.lower()} | {n.lower() for n in self.app_names}
            for app in NSWorkspace.sharedWorkspace().runningApplications():
                app_name = app.localizedName() or ""
                if app_name.lower() in target_names:
                    # NSApplicationActivateAllWindows | NSApplicationActivateIgnoringOtherApps
                    app.activateWithOptions_(3)
                    time.sleep(0.4)
                    return
        except Exception:
            pass
        # Fallback to AppleScript with alternative names.
        if _activate_macos_app(owner):
            time.sleep(0.3)
            return
        for name in self.app_names:
            if name.lower() == owner.lower():
                continue
            if _activate_macos_app(name):
                time.sleep(0.3)
                return

    def _sticky_browser_window_bounds(self) -> tuple[int, int, int, int, str] | None:
        """Keep capturing a browser Docs host while its title is temporarily loading."""
        if not self.prefer_browser_docs or not self._owner_is_browser(self._last_app_owner):
            return None
        return find_browser_host_window_bounds([self._last_app_owner])

    def _browser_handoff_window_bounds(self) -> tuple[int, int, int, int, str] | None:
        if self._browser_handoff_captures <= 0:
            return None
        browser = find_frontmost_browser_host_window_bounds(self.browser_app_names)
        if browser:
            self._browser_handoff_captures -= 1
            return browser
        return None

    def _frontmost_browser_docs_precheck_bounds(self) -> tuple[int, int, int, int, str] | None:
        """Inspect a frontmost browser Docs page before forcing app-first recovery."""
        if self.prefer_browser_docs or self._suppress_browser_precheck:
            return None
        return find_frontmost_browser_host_window_bounds(
            self.browser_app_names,
            title_keywords=self.browser_title_keywords,
        )

    def _owner_is_browser(self, owner: str) -> bool:
        owner_lower = owner.lower()
        return any(owner_lower == name.lower() for name in self.browser_app_names)


class StaticScreen:
    def __init__(self, path: Path):
        self.path = path

    def capture(self) -> Image.Image:
        image = Image.open(self.path)
        attach_capture_metadata(image, (0, 0, image.width, image.height), "static", "")
        return image


def save_png(image: Image.Image, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path.name


def capture_metadata(image: Image.Image) -> dict[str, object]:
    return {
        "screen_offset": image.info.get("screen_offset", (0, 0)),
        "screen_scale": image.info.get("screen_scale", (1.0, 1.0)),
        "window_bounds": image.info.get("window_bounds"),
        "capture_type": image.info.get("capture_type"),
        "app_name": image.info.get("app_name"),
        "capture_role": image.info.get("capture_role", ""),
    }


def save_grounding_crop(image: Image.Image, grounding: dict[str, object], path: Path, padding: int = 12) -> str:
    box = grounding.get("box_image")
    if not box:
        return ""
    x1 = int(getattr(box, "x1"))
    y1 = int(getattr(box, "y1"))
    x2 = int(getattr(box, "x2"))
    y2 = int(getattr(box, "y2"))
    left = max(0, min(x1, x2) - padding)
    top = max(0, min(y1, y2) - padding)
    right = min(image.width, max(x1, x2) + padding)
    bottom = min(image.height, max(y1, y2) + padding)
    if right <= left or bottom <= top:
        return ""
    path.parent.mkdir(parents=True, exist_ok=True)
    image.crop((left, top, right, bottom)).save(path)
    return path.name


def save_elements_overlay(
    image: Image.Image,
    elements: list[dict[str, object]],
    path: Path,
) -> str:
    if not elements:
        return ""
    annotated = image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    colors = ["cyan", "lime", "magenta", "orange", "white", "yellow"]
    drew_any = False
    for index, element in enumerate(elements, start=1):
        box = element.get("box_image")
        point = element.get("point_image")
        color = colors[(index - 1) % len(colors)]
        if isinstance(box, Box):
            draw.rectangle([box.x1, box.y1, box.x2, box.y2], outline=color, width=3)
            label_x = max(0, box.x1)
            label_y = max(0, box.y1 - 14)
            draw.rectangle([label_x, label_y, label_x + 22, label_y + 13], fill=color)
            draw.text((label_x + 3, label_y), str(index), fill="black")
            drew_any = True
        if isinstance(point, Point):
            r = 6
            draw.ellipse([point.x - r, point.y - r, point.x + r, point.y + r], outline=color, width=3)
            drew_any = True
    if not drew_any:
        return ""
    path.parent.mkdir(parents=True, exist_ok=True)
    annotated.save(path)
    return path.name


def visual_change(before: Image.Image, after: Image.Image) -> dict[str, object]:
    if before.size != after.size:
        return {"status": "changed:size", "mean_delta": None, "bbox": None}
    diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
    stat = ImageStat.Stat(diff)
    score = round(sum(stat.mean) / len(stat.mean), 3)
    bbox = diff.getbbox()
    if score < 0.5:
        status = "no-visible-change"
    elif score < 3:
        status = "small-change"
    else:
        status = "changed"
    return {"status": status, "mean_delta": score, "bbox": list(bbox) if bbox else None}


def attach_capture_metadata(
    image: Image.Image,
    region: tuple[int, int, int, int],
    capture_type: str,
    app_name: str,
) -> None:
    x, y, width, height = region
    image.info["screen_offset"] = (x, y)
    image.info["screen_scale"] = _image_to_screen_scale(image, width, height)
    image.info["window_bounds"] = region
    image.info["capture_type"] = capture_type
    image.info["app_name"] = app_name


def _image_to_screen_scale(image: Image.Image, screen_width: int, screen_height: int) -> tuple[float, float]:
    if image.width <= 0 or image.height <= 0:
        return (1.0, 1.0)
    return (float(screen_width) / float(image.width), float(screen_height) / float(image.height))


def _full_screen_region(image: Image.Image) -> tuple[int, int, int, int]:
    logical_size = _pyautogui_screen_size()
    if logical_size:
        return (0, 0, logical_size[0], logical_size[1])
    return (0, 0, image.width, image.height)


def _pyautogui_screen_size() -> tuple[int, int] | None:
    try:
        import pyautogui

        size = pyautogui.size()
        return (int(size.width), int(size.height))
    except Exception:
        return None


def find_preferred_window_bounds(
    app_names: list[str],
    *,
    browser_app_names: list[str] | None = None,
    browser_title_keywords: list[str] | None = None,
    prefer_browser_docs: bool = False,
    allow_browser_fallback: bool = True,
) -> tuple[int, int, int, int, str] | None:
    windows = _visible_windows()
    if not windows:
        return None

    if prefer_browser_docs:
        browser = _largest_matching_window(
            windows,
            app_names=browser_app_names or [],
            title_keywords=browser_title_keywords or [],
        )
        if browser:
            return browser

    app_window = _largest_matching_window(windows, app_names=app_names)
    if app_window:
        return app_window

    if not allow_browser_fallback:
        return None

    return _largest_matching_window(
        windows,
        app_names=browser_app_names or [],
        title_keywords=browser_title_keywords or [],
    )


def find_app_window_bounds(app_names: list[str]) -> tuple[int, int, int, int, str] | None:
    return _largest_matching_window(_visible_windows(), app_names=app_names)


def find_browser_host_window_bounds(browser_app_names: list[str]) -> tuple[int, int, int, int, str] | None:
    return _largest_matching_window(_visible_windows(), app_names=browser_app_names)


def find_frontmost_browser_host_window_bounds(
    browser_app_names: list[str],
    *,
    title_keywords: list[str] | None = None,
) -> tuple[int, int, int, int, str] | None:
    normalized_apps = {name.lower() for name in browser_app_names}
    normalized_keywords = [item.lower() for item in title_keywords or []]
    for window in _visible_windows():
        owner = str(window.get("kCGWindowOwnerName") or "")
        if owner.lower() not in normalized_apps:
            continue
        title = str(window.get("kCGWindowName") or "")
        if normalized_keywords and not any(keyword in title.lower() for keyword in normalized_keywords):
            continue
        bounds = window.get("kCGWindowBounds") or {}
        x = int(bounds.get("X", 0))
        y = int(bounds.get("Y", 0))
        width = int(bounds.get("Width", 0))
        height = int(bounds.get("Height", 0))
        return x, y, width, height, owner
    return None


def recover_visible_app_window(app_names: list[str]) -> bool:
    """Bring a likely Feishu/Docs host app to the foreground before recapturing."""
    if platform.system() != "Darwin":
        return False
    for name in app_names:
        if _activate_macos_app(name):
            return True
    return False


def recover_preferred_window_bounds(
    recovery_app_names: list[str],
    app_names: list[str],
    *,
    browser_app_names: list[str] | None = None,
    browser_title_keywords: list[str] | None = None,
    prefer_browser_docs: bool = False,
    allow_browser_fallback: bool = True,
) -> tuple[int, int, int, int, str] | None:
    """Activate each candidate app and return as soon as a preferred window appears."""
    if platform.system() != "Darwin":
        return None
    for name in recovery_app_names:
        if not _activate_macos_app(name):
            continue
        time.sleep(0.8)
        bounds = find_preferred_window_bounds(
            app_names,
            browser_app_names=browser_app_names,
            browser_title_keywords=browser_title_keywords,
            prefer_browser_docs=prefer_browser_docs,
            allow_browser_fallback=allow_browser_fallback,
        )
        if bounds:
            return bounds
    return None


def _activate_macos_app(name: str) -> bool:
    script = f'tell application "{_escape_applescript(name)}" to activate'
    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            timeout=2,
        )
        return completed.returncode == 0
    except Exception:
        return False


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _visible_windows() -> list[dict[str, object]]:
    if platform.system() != "Darwin":
        return []
    try:
        import Quartz
    except Exception:
        return []

    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    display_bounds = _active_display_bounds(Quartz)
    visible = []
    for window in windows:
        if window.get("kCGWindowLayer") != 0:
            continue
        bounds = window.get("kCGWindowBounds") or {}
        x = int(bounds.get("X", 0))
        y = int(bounds.get("Y", 0))
        width = int(bounds.get("Width", 0))
        height = int(bounds.get("Height", 0))
        if width <= 80 or height <= 80:
            continue
        if display_bounds and not _rect_intersects_any((x, y, width, height), display_bounds):
            continue
        visible.append(window)
    return visible


def _active_display_bounds(quartz) -> list[tuple[int, int, int, int]]:
    try:
        max_displays = 16
        _, displays, count = quartz.CGGetActiveDisplayList(max_displays, None, None)
    except Exception:
        return []
    bounds = []
    for display in list(displays or [])[: int(count or 0)]:
        try:
            rect = quartz.CGDisplayBounds(display)
            bounds.append((int(rect.origin.x), int(rect.origin.y), int(rect.size.width), int(rect.size.height)))
        except Exception:
            continue
    return bounds


def _rect_intersects_any(
    rect: tuple[int, int, int, int],
    candidates: list[tuple[int, int, int, int]],
) -> bool:
    x, y, width, height = rect
    if width <= 0 or height <= 0:
        return False
    right = x + width
    bottom = y + height
    for cx, cy, cwidth, cheight in candidates:
        cright = cx + cwidth
        cbottom = cy + cheight
        if x < cright and right > cx and y < cbottom and bottom > cy:
            return True
    return False


def _largest_matching_window(
    windows: list[dict[str, object]],
    *,
    app_names: list[str],
    title_keywords: list[str] | None = None,
) -> tuple[int, int, int, int, str] | None:
    normalized_apps = {name.lower() for name in app_names}
    normalized_keywords = [item.lower() for item in title_keywords or []]
    candidates = []
    for window in windows:
        owner = str(window.get("kCGWindowOwnerName") or "")
        title = str(window.get("kCGWindowName") or "")
        owner_matched = bool(normalized_apps) and owner.lower() in normalized_apps
        title_matched = bool(normalized_keywords) and any(keyword in title.lower() for keyword in normalized_keywords)
        if not owner_matched and not title_matched:
            continue
        if normalized_keywords and owner_matched and not title_matched:
            continue
        bounds = window.get("kCGWindowBounds") or {}
        x = int(bounds.get("X", 0))
        y = int(bounds.get("Y", 0))
        width = int(bounds.get("Width", 0))
        height = int(bounds.get("Height", 0))
        candidates.append((width * height, x, y, width, height, owner))
    if not candidates:
        return None
    _, x, y, width, height, owner = max(candidates, key=lambda item: item[0])
    return x, y, width, height, owner


def dismiss_macos_screenshot_overlay(image: Image.Image) -> bool:
    offset = image.info.get("screen_offset") or (0, 0)
    origin_x, origin_y = int(offset[0]), int(offset[1])
    width, height = image.size
    start_x = int(width * 0.80)
    start_y = int(height * 0.86)
    pixels = image.convert("RGB").load()
    red_pixels = []
    green_pixels = []
    for y in range(start_y, height):
        for x in range(start_x, width):
            r, g, b = pixels[x, y]
            if r > 210 and g < 110 and b < 110:
                red_pixels.append((x, y))
            elif g > 150 and r < 120 and b < 150:
                green_pixels.append((x, y))
    if len(red_pixels) < 8 or len(green_pixels) < 8:
        return False
    red_x = round(sum(x for x, _ in red_pixels) / len(red_pixels))
    red_y = round(sum(y for _, y in red_pixels) / len(red_pixels))
    green_x = round(sum(x for x, _ in green_pixels) / len(green_pixels))
    green_y = round(sum(y for _, y in green_pixels) / len(green_pixels))
    if red_y < start_y or green_y < start_y or green_x <= red_x:
        return False
    try:
        import pyautogui

        pyautogui.click(origin_x + red_x, origin_y + red_y)
        return True
    except Exception:
        return False
