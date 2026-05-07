from PIL import Image

from cua_lark.domain.models import Action, ActionKind, Box, Point, TestCase
from cua_lark.testing.grounding_check import (
    apply_grounding_check_response,
    build_grounding_check,
    grounding_check_risk,
    needs_grounding_check,
)


def test_build_grounding_check_marks_clickable_action():
    image = Image.new("RGB", (1000, 800), "white")
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 400),
        target="emoji button",
        grounding={"point_image": Point(500, 400), "box_image": Box(480, 380, 520, 420)},
    )
    case = TestCase(id="C-001", name="demo", instruction="click emoji", expected="")

    check = build_grounding_check(action, image, case)

    assert needs_grounding_check(action)
    assert check.annotated_image.size == image.size
    assert "red crosshair" in check.prompt
    assert "emoji button" in check.prompt


def test_apply_grounding_check_response_updates_corrected_point():
    image = Image.new("RGB", (1000, 800), "white")
    image.info["screen_offset"] = (100, 40)
    action = Action(kind=ActionKind.CLICK, point=Point(500, 400))
    raw = "Verdict: CORRECTED\nCorrectedPoint: <point>250 500</point>\nReason: better target"

    apply_grounding_check_response(action, raw, image.size, {"screen_offset": (100, 40)})

    assert action.point == Point(350, 440)
    assert action.grounding_check["changed_point"] is True
    assert action.grounding_check["corrected_point_0_1000"] == [250, 500]


def test_grounding_check_risk_triggers_dense_toolbar_target():
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 400),
        target="@ button in chat input toolbar",
        grounding={"box_0_1000": [850, 930, 880, 960], "point_0_1000": [865, 945]},
    )

    risk = grounding_check_risk(action, mode="high-risk")

    assert risk["triggered"] is True
    assert risk["reason"] == "small_grounding_box"


def test_grounding_check_risk_skips_plain_input_box():
    action = Action(kind=ActionKind.CLICK, point=Point(500, 400), target="message input area")

    risk = grounding_check_risk(action, mode="high-risk")

    assert risk == {"triggered": False, "mode": "high-risk", "reason": "text_input_focus_target"}


def test_grounding_check_risk_skips_wide_search_input_even_if_short():
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 400),
        target="top left search input box",
        thought="Click the search box to find 孙浩翔",
        grounding={
            "box_0_1000": [180, 80, 470, 110],
            "point_0_1000": [260, 94],
            "confidence": "0.96",
            "evidence": "wide search input field",
        },
    )

    risk = grounding_check_risk(action, mode="high-risk")

    assert risk["triggered"] is False
    assert risk["reason"] == "text_input_focus_target"


def test_grounding_check_risk_skips_large_conversation_list_entry():
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 400),
        target="孙浩翔 conversation entry",
        thought="Click the conversation entry for 孙浩翔 in the recent message list",
        grounding={
            "box_0_1000": [10, 120, 380, 190],
            "point_0_1000": [315, 161],
            "confidence": "0.99",
            "evidence": "visible in recent message list",
        },
    )

    risk = grounding_check_risk(action, mode="high-risk")

    assert risk["triggered"] is False
    assert risk["reason"] == "self_consistent_large_target"
    assert risk["point_inside_box"] is True


def test_grounding_check_risk_triggers_point_outside_bbox():
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 400),
        target="@ button",
        grounding={
            "box_0_1000": [850, 930, 870, 960],
            "point_0_1000": [890, 945],
            "confidence": "0.99",
        },
    )

    risk = grounding_check_risk(action, mode="high-risk")

    assert risk["triggered"] is True
    assert risk["reason"] == "point_outside_grounding_box"
    assert risk["point_inside_box"] is False


def test_grounding_check_risk_triggers_low_confidence_large_target():
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 400),
        target="message input area",
        grounding={
            "box_0_1000": [430, 920, 980, 970],
            "point_0_1000": [545, 945],
            "confidence": "0.70",
        },
    )

    risk = grounding_check_risk(action, mode="high-risk")

    assert risk["triggered"] is True
    assert risk["reason"] == "low_grounding_confidence"


def test_grounding_check_risk_still_triggers_input_point_outside_bbox():
    action = Action(
        kind=ActionKind.CLICK,
        point=Point(500, 400),
        target="message input area",
        grounding={
            "box_0_1000": [430, 920, 980, 970],
            "point_0_1000": [300, 945],
            "confidence": "0.97",
        },
    )

    risk = grounding_check_risk(action, mode="high-risk")

    assert risk["triggered"] is True
    assert risk["reason"] == "point_outside_grounding_box"
