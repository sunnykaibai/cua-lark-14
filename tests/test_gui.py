from cua_lark.adapters.gui import PyAutoGui
from cua_lark.domain.models import Action, ActionKind


class FakePyAutoGui:
    FAILSAFE = False
    PAUSE = 0

    def __init__(self):
        self.calls = []

    def keyDown(self, key):
        self.calls.append(("down", key))

    def keyUp(self, key):
        self.calls.append(("up", key))

    def press(self, key):
        self.calls.append(("press", key))


class FakeSettings:
    executor = {}


def test_hotkey_uses_explicit_key_down_and_reverse_key_up(monkeypatch):
    fake = FakePyAutoGui()

    def fake_import(name, *args, **kwargs):
        if name == "pyautogui":
            return fake
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fake_import)
    gui = PyAutoGui(FakeSettings())

    gui.execute(Action(kind=ActionKind.HOTKEY, key="command v"))

    assert fake.calls == [
        ("down", "command"),
        ("down", "v"),
        ("up", "v"),
        ("up", "command"),
    ]
