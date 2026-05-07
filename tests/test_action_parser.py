from cua_lark.domain.action_parser import parse_action
from cua_lark.domain.models import ActionKind


def test_parse_click_scales_normalized_point():
    action = parse_action(
        "\n".join(
            [
                "Thought: click the search box",
                "Grounding: target='search box', bbox='<box>100 200 300 400</box>', point='<point>200 300</point>', confidence='0.90', evidence='visible'",
                "Expected: the search box receives focus",
                "Action: click(point='<point>200 300</point>')",
            ]
        ),
        (2000, 1000),
    )

    assert action.kind == ActionKind.CLICK
    assert action.point.x == 400
    assert action.point.y == 300
    assert action.grounding["target"] == "search box"


def test_parse_click_adds_window_offset_to_screen_point():
    action = parse_action(
        "Action: click(point='<point>500 500</point>')",
        (1000, 800),
        {"screen_offset": (100, 40), "screen_scale": (1.0, 1.0)},
    )

    assert action.point.x == 600
    assert action.point.y == 440


def test_parse_type_clear_existing():
    action = parse_action("Action: type(content='hello', clear_existing='true')", (100, 100))

    assert action.kind == ActionKind.TYPE_TEXT
    assert action.text == "hello"
    assert action.clear_existing is True


def test_parse_type_unescapes_newlines_from_model_string():
    action = parse_action(
        'Action: type(content="第一行\\n第二行\\n# Markdown 标题")',
        (100, 100),
    )

    assert action.kind == ActionKind.TYPE_TEXT
    assert action.text == "第一行\n第二行\n# Markdown 标题"


def test_parse_type_accepts_multiline_action_content():
    action = parse_action(
        "\n".join(
            [
                "Thought: paste markdown material",
                "Action: type(content='# DOCS-FEATURE-MATERIAL-ROOT-7A2D",
                "",
                "正文第一段",
                "## 二级标题",
                "DOCS-FEATURE-MATERIAL-END-0B5C')",
            ]
        ),
        (100, 100),
    )

    assert action.kind == ActionKind.TYPE_TEXT
    assert action.text.startswith("# DOCS-FEATURE-MATERIAL-ROOT-7A2D")
    assert "## 二级标题" in action.text
    assert action.text.endswith("DOCS-FEATURE-MATERIAL-END-0B5C")


def test_parse_type_allows_quotes_inside_multiline_content():
    action = parse_action(
        "Action: type(content=\"const docsFeatureProbe = 'DOCS-FEATURE-CODE-B8A4';\")",
        (100, 100),
    )

    assert action.kind == ActionKind.TYPE_TEXT
    assert action.text == "const docsFeatureProbe = 'DOCS-FEATURE-CODE-B8A4';"


def test_parse_type_accepts_material_reference_token():
    action = parse_action("Action: type(content='{material:docs-feature-material.md}')", (100, 100))

    assert action.kind == ActionKind.TYPE_TEXT
    assert action.text == "{material:docs-feature-material.md}"


def test_parse_grounding_accepts_bbox_tag():
    action = parse_action(
        "\n".join(
            [
                "Grounding: target='send button', bbox='<bbox>942 936 966 958</bbox>', point='<point>954 947</point>', confidence='0.99', evidence='visible'",
                "Action: click(point='<point>954 947</point>')",
            ]
        ),
        (1000, 1000),
    )

    assert action.grounding["box_0_1000"] == [942, 936, 966, 958]


def test_parse_grounding_accepts_legacy_point_tag_for_bbox_value():
    action = parse_action(
        "\n".join(
            [
                "Grounding: target='mention option', bbox='<point>438 850 975 879</point>', point='<point>485 865</point>', confidence='1.00', evidence='visible'",
                "Action: click(point='<point>485 865</point>')",
            ]
        ),
        (1000, 1000),
    )

    assert action.grounding["box_0_1000"] == [438, 850, 975, 879]


def test_parse_elements_adds_multi_target_grounding():
    action = parse_action(
        "\n".join(
            [
                "Thought: click the @ button",
                "Grounding: target='@ button', bbox='<box>850 930 880 960</box>', point='<point>865 945</point>', confidence='0.92', evidence='toolbar icon'",
                'Elements: [{"name":"message input box","role":"reusable_context","bbox":[420,900,820,980],"point":[620,940],"confidence":0.96,"evidence":"bottom composer"},{"name":"@ button","role":"action_target","bbox":[850,930,880,960],"point":[865,945],"confidence":0.92,"evidence":"toolbar at icon"}]',
                "Action: click(point='<point>865 945</point>')",
            ]
        ),
        (2000, 1000),
        {"screen_offset": (100, 40), "screen_scale": (1.0, 1.0)},
    )

    elements = action.grounding["elements"]
    assert len(elements) == 2
    assert elements[0]["name"] == "message input box"
    assert elements[0]["box_0_1000"] == [420, 900, 820, 980]
    assert elements[0]["point_image"].x == 1240
    assert elements[0]["point_screen"].y == 980
    assert elements[1]["role"] == "action_target"


def test_parse_elements_accepts_multiline_json_block():
    action = parse_action(
        "\n".join(
            [
                "Thought: click Feishu",
                "Grounding: target='Feishu app icon', bbox='<bbox>86 214 109 250</bbox>', point='<point>97 232</point>', confidence='0.95', evidence='visible icon'",
                "Elements: [",
                '{"name":"Feishu app icon","role":"action_target","bbox":[86,214,109,250],"point":[97,232],"confidence":0.95,"evidence":"visible icon"},',
                '{"name":"VS Code main window","role":"nearby_confuser","bbox":[101,51,898,908],"point":[499,480],"confidence":1.0,"evidence":"foreground window"}',
                "]",
                "Expected: Feishu comes to foreground",
                "Action: click(point='<point>97 232</point>')",
            ]
        ),
        (1000, 1000),
    )

    elements = action.grounding["elements"]
    assert len(elements) == 2
    assert elements[0]["name"] == "Feishu app icon"
    assert elements[1]["role"] == "nearby_confuser"


def test_parse_batch_actions_json_block():
    action = parse_action(
        "\n".join(
            [
                "Thought: focus and type into Docs body",
                "CompletionCheck: not_satisfied - body text is not visible yet",
                "Action: batch()",
                "Actions: [",
                '{"action":"click","target":"Docs body","point":[500,620],"evidence":"body insertion point"},',
                '{"action":"type_text","target":"Docs body","content":"DOCS-BATCH-PROBE"}',
                "]",
            ]
        ),
        (1000, 1000),
    )

    assert action.kind == ActionKind.BATCH
    assert action.completion_check["status"] == "not_satisfied"
    assert len(action.sub_actions) == 2
    assert action.sub_actions[0].kind == ActionKind.CLICK
    assert action.sub_actions[0].point.x == 500
    assert action.sub_actions[1].kind == ActionKind.TYPE_TEXT
    assert action.sub_actions[1].text == "DOCS-BATCH-PROBE"


def test_parse_new_system_prompt_single_action_shape():
    action = parse_action(
        "\n".join(
            [
                'CompletionCheck: {"status":"not_satisfied","reason":"target anchor is visible but table is not present","last_action_result":"matched"}',
                "Thought: Click the paragraph after the table anchor to place the insertion cursor.",
                "Grounding: target='paragraph after DOCS-FEATURE-TABLE-ANCHOR-3C2A', bbox='<box>420 500 900 548</box>', point='<point>500 526</point>', confidence='0.95', evidence='The target anchor line is visible and the click point is in the following paragraph area.'",
                "Action: click(point='<point>500 526</point>')",
                "Expected: the insertion cursor is placed after the table anchor line",
            ]
        ),
        (1000, 1000),
    )

    assert action.kind == ActionKind.CLICK
    assert action.completion_check["status"] == "not_satisfied"
    assert action.completion_check["last_action_result"] == "matched"
    assert action.grounding["target"] == "paragraph after DOCS-FEATURE-TABLE-ANCHOR-3C2A"
    assert action.expected == "the insertion cursor is placed after the table anchor line"


def test_parse_new_system_prompt_finished_shape():
    action = parse_action(
        "\n".join(
            [
                'CompletionCheck: {"status":"satisfied","reason":"the target title and required anchor are visible","last_action_result":"matched"}',
                "Thought: The target document already contains the required material.",
                "Action: finished(content='The target document is open and contains the required anchors.')",
                "Grounding: none",
                "Expected: task is complete in the current screenshot",
            ]
        ),
        (1000, 1000),
    )

    assert action.kind == ActionKind.FINISHED
    assert action.completion_check["status"] == "satisfied"
    assert action.text == "The target document is open and contains the required anchors."


def test_parse_batch_inline_json_payload():
    action = parse_action(
        'Action: batch([{"action":"type","content":"DOCS-FEATURE-STRUCTURE-TARGET-4B11","clear_existing":"true"},{"action":"hotkey","key":"enter"}])',
        (1000, 1000),
    )

    assert action.kind == ActionKind.BATCH
    assert len(action.sub_actions) == 2
    assert action.sub_actions[0].kind == ActionKind.TYPE_TEXT
    assert action.sub_actions[0].text == "DOCS-FEATURE-STRUCTURE-TARGET-4B11"
    assert action.sub_actions[0].clear_existing is True
    assert action.sub_actions[1].kind == ActionKind.HOTKEY
    assert action.sub_actions[1].key == "enter"


def test_parse_batch_inline_actions_keyword_payload():
    action = parse_action(
        'Action: batch(actions=[{"action":"click","point":"<point>287 306</point>"},{"action":"type_text","content":"CUA-Lark Docs 冒烟输入"}])',
        (1000, 1000),
    )

    assert action.kind == ActionKind.BATCH
    assert len(action.sub_actions) == 2
    assert action.sub_actions[0].kind == ActionKind.CLICK
    assert action.sub_actions[0].point.x == 287
    assert action.sub_actions[1].kind == ActionKind.TYPE_TEXT
    assert action.sub_actions[1].text == "CUA-Lark Docs 冒烟输入"


def test_parse_batch_inline_actions_colon_payload():
    action = parse_action(
        'Action: batch(Actions: [{"action":"click","point":"<point>300 630</point>"},{"action":"type_text","content":"DOCS-P2-003 正文编辑验证"}])',
        (1000, 1000),
    )

    assert action.kind == ActionKind.BATCH
    assert len(action.sub_actions) == 2
    assert action.sub_actions[0].kind == ActionKind.CLICK
    assert action.sub_actions[0].point.y == 630
    assert action.sub_actions[1].kind == ActionKind.TYPE_TEXT
    assert action.sub_actions[1].text == "DOCS-P2-003 正文编辑验证"


def test_parse_batch_multiline_json_payload():
    action = parse_action(
        "\n".join(
            [
                "Thought: insert divider",
                "Action: batch(",
                "    [",
                '        {"action": "click", "point": [275, 929]},',
                '        {"action": "hotkey", "key": "delete"},',
                '        {"action": "hotkey", "key": "enter"}',
                "    ]",
                ")",
                'Elements: [{"name":"divider line","point":[275,929]}]',
            ]
        ),
        (1000, 1000),
    )

    assert action.kind == ActionKind.BATCH
    assert len(action.sub_actions) == 3
    assert action.sub_actions[0].kind == ActionKind.CLICK
    assert action.sub_actions[1].kind == ActionKind.HOTKEY
    assert action.sub_actions[1].key == "delete"
    assert action.sub_actions[2].key == "enter"


def test_parse_batch_multiline_inline_actions_block():
    action = parse_action(
        "\n".join(
            [
                "Thought: search in find box",
                "Action: batch(",
                "Actions: [",
                '{"action": "hotkey", "key": "command a"},',
                '{"action": "type", "content": "DOCS-FEATURE-SEARCH-EDIT-0A52"},',
                '{"action": "hotkey", "key": "enter"}',
                "]",
                ")",
            ]
        ),
        (1000, 1000),
    )

    assert action.kind == ActionKind.BATCH
    assert len(action.sub_actions) == 3
    assert action.sub_actions[0].kind == ActionKind.HOTKEY
    assert action.sub_actions[1].kind == ActionKind.TYPE_TEXT
    assert action.sub_actions[1].text == "DOCS-FEATURE-SEARCH-EDIT-0A52"
    assert action.sub_actions[2].key == "enter"
