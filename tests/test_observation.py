from cua_lark.domain.models import Action, ActionKind, Point
from cua_lark.testing.observation import interpret_visual_change


def test_interpret_visual_change_marks_input_click_as_focus_likely():
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 930),
        target="message input box",
        grounding={"box_0_1000": [430, 900, 980, 970], "point_0_1000": [520, 935]},
    )

    observed = interpret_visual_change(action, {"status": "no-visible-change", "mean_delta": 0.003, "bbox": [666, 883, 670, 901]})

    assert observed["status"] == "focus-likely"
    assert observed["raw_status"] == "no-visible-change"
    assert observed["reason"] == "input_click_cursor_blink_or_existing_focus"


def test_interpret_visual_change_keeps_non_input_no_change():
    action = Action(kind=ActionKind.CLICK, point=Point(80, 80), target="settings button")

    observed = interpret_visual_change(action, {"status": "no-visible-change", "mean_delta": 0.0, "bbox": None})

    assert observed == {"status": "no-visible-change", "mean_delta": 0.0, "bbox": None}


def test_interpret_visual_change_does_not_treat_docs_title_click_as_verified_focus():
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 300),
        target="文档标题字段",
        thought="点击显示“请输入标题”的文档标题字段",
    )

    observed = interpret_visual_change(action, {"status": "no-visible-change", "mean_delta": 0.019, "bbox": [1229, 18, 3428, 751]})

    assert observed["status"] == "no-visible-change"


def test_interpret_visual_change_does_not_trust_docs_body_intent_words_only():
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 330),
        target="document body editor",
        thought="Click here to activate the text input cursor",
        grounding={"box_0_1000": [336, 289, 537, 326], "point_0_1000": [432, 308]},
    )

    observed = interpret_visual_change(action, {"status": "small-change", "mean_delta": 1.0, "bbox": [0, 0, 10, 10]})

    assert observed["status"] == "small-change"
