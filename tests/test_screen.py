from pathlib import Path

from PIL import Image

from cua_lark.adapters.screen import (
    PyAutoGuiScreen,
    _largest_matching_window,
    attach_capture_metadata,
    capture_metadata,
    find_frontmost_browser_host_window_bounds,
    save_grounding_crop,
)
from cua_lark.domain.models import Box


def test_save_grounding_crop(tmp_path: Path):
    image = Image.new("RGB", (100, 100), "white")
    output = save_grounding_crop(image, {"box_image": Box(20, 20, 40, 40)}, tmp_path / "crop.png")

    assert output == "crop.png"
    assert (tmp_path / "crop.png").exists()


def test_attach_capture_metadata_sets_retina_image_to_screen_scale():
    image = Image.new("RGB", (2000, 1000), "white")

    attach_capture_metadata(image, (0, 0, 1000, 500), "full_screen", "")

    metadata = capture_metadata(image)
    assert metadata["screen_scale"] == (0.5, 0.5)


def test_largest_matching_window_requires_browser_title_keyword_when_provided():
    windows = [
        {
            "kCGWindowOwnerName": "Safari",
            "kCGWindowName": "普通网页",
            "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 1600, "Height": 900},
        },
        {
            "kCGWindowOwnerName": "Safari",
            "kCGWindowName": "未命名文档 - 飞书云文档",
            "kCGWindowBounds": {"X": 10, "Y": 20, "Width": 1200, "Height": 800},
        },
    ]

    selected = _largest_matching_window(windows, app_names=["Safari"], title_keywords=["飞书云文档"])

    assert selected == (10, 20, 1200, 800, "Safari")


def test_largest_matching_window_selects_feishu_app_without_title_keyword():
    windows = [
        {
            "kCGWindowOwnerName": "飞书",
            "kCGWindowName": "消息",
            "kCGWindowBounds": {"X": 100, "Y": 100, "Width": 800, "Height": 600},
        },
        {
            "kCGWindowOwnerName": "飞书",
            "kCGWindowName": "云文档",
            "kCGWindowBounds": {"X": 50, "Y": 50, "Width": 1000, "Height": 700},
        },
    ]

    selected = _largest_matching_window(windows, app_names=["飞书"])

    assert selected == (50, 50, 1000, 700, "飞书")


def test_required_app_window_recovers_before_refusing_fullscreen_fallback(monkeypatch):
    screen = PyAutoGuiScreen(
        prefer_app_window=True,
        prefer_browser_docs=True,
        require_app_window=True,
        app_recovery_names=["Safari"],
        recovery_attempts=1,
    )
    calls = {"find": 0, "recover": 0}

    def fake_find(*args, **kwargs):
        calls["find"] += 1
        if calls["find"] == 1:
            return None
        return (10, 20, 300, 200, "Safari")

    monkeypatch.setattr("cua_lark.adapters.screen.find_preferred_window_bounds", fake_find)
    monkeypatch.setattr(
        "cua_lark.adapters.screen.recover_preferred_window_bounds",
        lambda *args, **kwargs: calls.__setitem__("recover", calls["recover"] + 1) or fake_find(),
    )

    assert screen._find_or_recover_window() == (10, 20, 300, 200, "Safari")
    assert calls == {"find": 2, "recover": 1}


def test_optional_fullscreen_fallback_still_recovers_first(monkeypatch):
    screen = PyAutoGuiScreen(
        prefer_app_window=True,
        prefer_browser_docs=True,
        require_app_window=False,
        app_recovery_names=["Safari"],
        recovery_attempts=1,
    )
    calls = {"find": 0, "recover": 0}

    def fake_find(*args, **kwargs):
        calls["find"] += 1
        if calls["find"] == 1:
            return None
        return (10, 20, 300, 200, "Safari")

    monkeypatch.setattr("cua_lark.adapters.screen.find_preferred_window_bounds", fake_find)
    monkeypatch.setattr(
        "cua_lark.adapters.screen.recover_preferred_window_bounds",
        lambda *args, **kwargs: calls.__setitem__("recover", calls["recover"] + 1) or fake_find(),
    )

    assert screen._find_or_recover_window() == (10, 20, 300, 200, "Safari")
    assert calls == {"find": 2, "recover": 1}


def test_optional_docs_capture_prefers_browser_window_before_fullscreen(monkeypatch):
    screen = PyAutoGuiScreen(
        prefer_app_window=True,
        prefer_browser_docs=True,
        require_app_window=False,
        browser_app_names=["Safari"],
        app_recovery_names=["飞书"],
        recovery_attempts=1,
    )

    monkeypatch.setattr("cua_lark.adapters.screen.find_preferred_window_bounds", lambda *args, **kwargs: None)
    monkeypatch.setattr("cua_lark.adapters.screen.recover_visible_app_window", lambda names: False)
    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_browser_host_window_bounds",
        lambda names: (20, 30, 1200, 800, "Safari"),
    )

    assert screen._find_or_recover_window() == (20, 30, 1200, 800, "Safari")


def test_browser_docs_capture_stays_on_last_browser_host_while_title_loads(monkeypatch):
    screen = PyAutoGuiScreen(
        prefer_app_window=True,
        prefer_browser_docs=True,
        browser_app_names=["Safari"],
        recovery_attempts=0,
    )
    screen._last_app_owner = "Safari"

    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_browser_host_window_bounds",
        lambda names: (20, 30, 1200, 800, "Safari"),
    )
    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_preferred_window_bounds",
        lambda *args, **kwargs: (100, 100, 900, 700, "飞书"),
    )

    assert screen._find_or_recover_window() == (20, 30, 1200, 800, "Safari")


def test_browser_handoff_temporarily_prefers_frontmost_browser(monkeypatch):
    screen = PyAutoGuiScreen(
        prefer_app_window=True,
        prefer_browser_docs=False,
        browser_app_names=["Safari"],
        recovery_attempts=0,
    )
    screen.arm_browser_handoff(captures=1)

    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_frontmost_browser_host_window_bounds",
        lambda names, **kwargs: (20, 30, 1200, 800, "Safari") if not kwargs.get("title_keywords") else None,
    )
    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_preferred_window_bounds",
        lambda *args, **kwargs: (100, 100, 900, 700, "飞书"),
    )

    assert screen._find_or_recover_window() == (20, 30, 1200, 800, "Safari")
    assert screen._find_or_recover_window() == (100, 100, 900, 700, "飞书")


def test_frontmost_browser_docs_precheck_before_app_first(monkeypatch):
    screen = PyAutoGuiScreen(
        prefer_app_window=True,
        prefer_browser_docs=False,
        browser_app_names=["Safari"],
        browser_title_keywords=["飞书云文档"],
        recovery_attempts=0,
    )

    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_frontmost_browser_host_window_bounds",
        lambda names, **kwargs: (20, 30, 1200, 800, "Safari") if kwargs.get("title_keywords") == ["飞书云文档"] else None,
    )
    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_preferred_window_bounds",
        lambda *args, **kwargs: (100, 100, 900, 700, "飞书"),
    )

    assert screen._find_or_recover_window() == (20, 30, 1200, 800, "Safari")


def test_browser_precheck_requires_docs_title_keywords(monkeypatch):
    screen = PyAutoGuiScreen(
        prefer_app_window=True,
        prefer_browser_docs=False,
        browser_app_names=["Safari"],
        browser_title_keywords=["飞书云文档"],
        recovery_attempts=0,
    )

    monkeypatch.setattr("cua_lark.adapters.screen.find_frontmost_browser_host_window_bounds", lambda names, **kwargs: None)
    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_preferred_window_bounds",
        lambda *args, **kwargs: (100, 100, 900, 700, "飞书"),
    )

    assert screen._find_or_recover_window() == (100, 100, 900, 700, "飞书")


def test_browser_handoff_clears_precheck_suppression(monkeypatch):
    screen = PyAutoGuiScreen(
        prefer_app_window=True,
        prefer_browser_docs=False,
        browser_app_names=["Safari"],
        browser_title_keywords=["飞书云文档"],
        recovery_attempts=0,
    )
    screen.suppress_browser_precheck()
    screen.arm_browser_handoff(captures=1)

    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_frontmost_browser_host_window_bounds",
        lambda names, **kwargs: (20, 30, 1200, 800, "Safari"),
    )
    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_preferred_window_bounds",
        lambda *args, **kwargs: (100, 100, 900, 700, "飞书"),
    )

    assert screen._find_or_recover_window() == (20, 30, 1200, 800, "Safari")
    assert screen._find_or_recover_window() == (20, 30, 1200, 800, "Safari")


def test_reset_transient_capture_state_reenables_browser_precheck(monkeypatch):
    screen = PyAutoGuiScreen(
        prefer_app_window=True,
        prefer_browser_docs=False,
        browser_app_names=["Safari"],
        browser_title_keywords=["飞书云文档"],
        recovery_attempts=0,
    )
    screen.suppress_browser_precheck()
    screen.reset_transient_capture_state()

    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_frontmost_browser_host_window_bounds",
        lambda names, **kwargs: (20, 30, 1200, 800, "Safari") if kwargs.get("title_keywords") == ["飞书云文档"] else None,
    )
    monkeypatch.setattr(
        "cua_lark.adapters.screen.find_preferred_window_bounds",
        lambda *args, **kwargs: (100, 100, 900, 700, "飞书"),
    )

    assert screen._find_or_recover_window() == (20, 30, 1200, 800, "Safari")


def test_frontmost_browser_host_uses_window_order(monkeypatch):
    windows = [
        {
            "kCGWindowOwnerName": "Safari",
            "kCGWindowName": "Loading",
            "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 1000, "Height": 700},
        },
        {
            "kCGWindowOwnerName": "Google Chrome",
            "kCGWindowName": "Other",
            "kCGWindowBounds": {"X": 10, "Y": 10, "Width": 1200, "Height": 800},
        },
    ]
    monkeypatch.setattr("cua_lark.adapters.screen._visible_windows", lambda: windows)

    assert find_frontmost_browser_host_window_bounds(["Safari", "Google Chrome"]) == (0, 0, 1000, 700, "Safari")


def test_required_app_window_refuses_fullscreen_after_recovery_fails(monkeypatch):
    screen = PyAutoGuiScreen(prefer_app_window=True, prefer_browser_docs=True, require_app_window=True, recovery_attempts=1)
    monkeypatch.setattr("cua_lark.adapters.screen.find_preferred_window_bounds", lambda *args, **kwargs: None)
    monkeypatch.setattr("cua_lark.adapters.screen.recover_visible_app_window", lambda names: False)

    try:
        screen.capture()
    except RuntimeError as exc:
        assert "after environment recovery" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
