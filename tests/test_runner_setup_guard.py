import pytest

from cua_lark.domain.models import Action, ActionKind, CaseResult, Status, StepResult, TestCase
from cua_lark.testing.runner import (
    _accept_docs_share_success_despite_verifier_fail,
    _ensure_action_allowed,
    _ensure_required_rule_modules,
    _guard_setup_action,
    _guard_unsafe_gui_action,
    _normal_macos_app_name,
    _suppress_docs_divider_menu_loop,
    _split_docs_divider_focus_from_shortcut_batch,
    _suppress_repeated_docs_divider_shortcut,
    _suppress_early_docs_table_repair_finish,
    _suppress_repeated_docs_bold_toggle,
    _suppress_repeated_docs_structure_insertion_click,
    _suppress_browser_precheck_action,
    _needs_feishu_host_activation,
    _verifier_passed,
)


def test_setup_guard_blocks_editor_close_button():
    case = TestCase(
        id="DOCS-ENTRY-001-SETUP",
        name="setup",
        instruction="setup",
        expected="ready",
        product="Docs",
        stage="docs_entry_robustness_setup",
    )
    action = Action(
        kind=ActionKind.CLICK,
        target="VS Code window red close button",
        thought="Click the red close button to reveal Feishu",
    )

    with pytest.raises(ValueError, match="blocked unsafe Docs action"):
        _guard_setup_action(case, action, {"capture_type": "full_screen", "app_name": ""})


def test_setup_guard_blocks_fullscreen_click_without_feishu_host_evidence():
    case = TestCase(
        id="DOCS-ENTRY-001-SETUP",
        name="setup",
        instruction="setup",
        expected="ready",
        product="Docs",
        stage="docs_entry_robustness_setup",
    )
    action = Action(kind=ActionKind.CLICK, target="unrelated app button", thought="Click unrelated app")

    with pytest.raises(ValueError, match="full-screen capture without Feishu/Docs host evidence"):
        _guard_setup_action(case, action, {"capture_type": "full_screen", "app_name": ""})


def test_docs_guard_blocks_fullscreen_hotkey_without_feishu_host_evidence():
    case = TestCase(
        id="DOCS-FEAT-FMT-001",
        name="加粗指定文本",
        instruction="打开文档，把指定文本设置为加粗",
        expected="目标文本加粗",
        product="Docs",
        stage="docs_formatting",
    )
    action = Action(kind=ActionKind.HOTKEY, key="command k", target="Feishu Docs search trigger")

    with pytest.raises(ValueError, match="full-screen capture without Feishu/Docs host evidence"):
        _guard_unsafe_gui_action(case, action, {"capture_type": "full_screen", "app_name": ""})


def test_setup_guard_allows_feishu_docs_target():
    case = TestCase(
        id="DOCS-ENTRY-001-SETUP",
        name="setup",
        instruction="setup",
        expected="ready",
        product="Docs",
        stage="docs_entry_robustness_setup",
    )
    action = Action(kind=ActionKind.CLICK, target="飞书云文档 home button", thought="Open Docs home")

    _guard_setup_action(case, action, {"capture_type": "app_window", "app_name": "飞书"})


def test_docs_guard_blocks_system_ui_outside_setup():
    case = TestCase(
        id="DOCS-SMOKE-001",
        name="进入云文档首页",
        instruction="打开飞书云文档首页",
        expected="Docs home",
        product="Docs",
        stage="docs_shell_smoke",
    )
    action = Action(kind=ActionKind.CLICK, target="Feishu menu item in the macOS menu bar")

    with pytest.raises(ValueError, match="blocked unsafe Docs action"):
        _guard_unsafe_gui_action(case, action, {"capture_type": "full_screen", "app_name": ""})


def test_docs_guard_allows_docs_find_popup_close_button():
    case = TestCase(
        id="DOCS-FEAT-FMT-001",
        name="加粗指定文本",
        instruction="打开文档，把指定文本设置为加粗",
        expected="目标文本加粗",
        product="Docs",
        stage="docs_formatting",
    )
    action = Action(kind=ActionKind.CLICK, target="Find popup close button")

    _guard_unsafe_gui_action(case, action, {"capture_type": "app_window", "app_name": "飞书"})


def test_docs_guard_allows_exact_target_browser_tab_shortcut():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="打开“CUA-Lark Docs Layer6 R4 Clean 20260501”，找到锚点后插入表格",
        expected="目标文档中出现表格",
        product="Docs",
        stage="docs_realistic_composition",
    )
    action = Action(
        kind=ActionKind.CLICK,
        target="Browser tab for CUA-Lark Docs Layer6 R4 Clean 20260501",
        thought="Click the visible target document browser tab",
    )

    _guard_unsafe_gui_action(case, action, {"capture_type": "app_window", "app_name": "Safari浏览器"})


def test_docs_guard_blocks_non_target_browser_tab():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="打开“CUA-Lark Docs Layer6 R4 Clean 20260501”，找到锚点后插入表格",
        expected="目标文档中出现表格",
        product="Docs",
        stage="docs_realistic_composition",
    )
    action = Action(
        kind=ActionKind.CLICK,
        target="Browser tab for unrelated page",
        thought="Click another browser tab",
    )

    with pytest.raises(ValueError, match="blocked unsafe Docs action"):
        _guard_unsafe_gui_action(case, action, {"capture_type": "app_window", "app_name": "Safari浏览器"})


def test_docs_guard_does_not_treat_table_anchor_as_browser_tab():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="打开“CUA-Lark Docs Layer6 R4 Clean 20260501”，找到锚点后插入表格",
        expected="目标文档中出现表格",
        product="Docs",
        stage="docs_realistic_composition",
    )
    action = Action(
        kind=ActionKind.HOTKEY,
        key="command f",
        target="Feishu Docs editor page",
        thought='Search for the target anchor "DOCS-FEATURE-TABLE-ANCHOR-3C2A"',
    )

    _guard_unsafe_gui_action(case, action, {"capture_type": "app_window", "app_name": "Safari浏览器"})


def test_runner_suppresses_early_finish_for_dirty_table_repair_case():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="在锚点后插入表格；如果看到数据堆在同一批单元格里，必须修复。",
        expected="表头和数据必须在不同表格行，中间有横向行边界",
        product="Docs",
        stage="docs_realistic_composition",
    )
    action = Action(kind=ActionKind.FINISHED, text="looks complete")

    suppressed = _suppress_early_docs_table_repair_finish(case, action, [])

    assert suppressed.kind == ActionKind.WAIT
    assert suppressed.target == "suppressed early table repair finish"


def test_runner_allows_finish_after_real_dirty_table_repair_edit():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="在锚点后插入表格；如果看到数据堆在同一批单元格里，必须修复。",
        expected="表头和数据必须在不同表格行，中间有横向行边界",
        product="Docs",
        stage="docs_realistic_composition",
    )
    action = Action(kind=ActionKind.FINISHED, text="looks complete")
    steps = [StepResult(index=1, action=Action(kind=ActionKind.HOTKEY, key="command x"))]

    suppressed = _suppress_early_docs_table_repair_finish(case, action, steps)

    assert suppressed.kind == ActionKind.FINISHED


def test_runner_suppresses_repeated_divider_menu_loop():
    case = TestCase(
        id="DOCS-FEAT-COMP-003",
        name="插入分割线分隔两段",
        instruction="在两段之间插入一条分割线",
        expected="两段之间可见水平分割线",
        product="Docs",
        stage="docs_realistic_composition",
    )
    history = [
        StepResult(index=1, action=Action(kind=ActionKind.SCROLL, target="insert block pop-up menu")),
        StepResult(index=2, action=Action(kind=ActionKind.CLICK, target="更多 option in insert block menu")),
    ]
    action = Action(kind=ActionKind.SCROLL, target="open insert block pop-up menu")

    suppressed = _suppress_docs_divider_menu_loop(case, action, history)

    assert suppressed.kind == ActionKind.HOTKEY
    assert suppressed.key == "esc"


def test_runner_does_not_suppress_first_divider_menu_scroll():
    case = TestCase(
        id="DOCS-FEAT-COMP-003",
        name="插入分割线分隔两段",
        instruction="在两段之间插入一条分割线",
        expected="两段之间可见水平分割线",
        product="Docs",
        stage="docs_realistic_composition",
    )
    action = Action(kind=ActionKind.SCROLL, target="open insert block pop-up menu")

    suppressed = _suppress_docs_divider_menu_loop(case, action, [])

    assert suppressed is action


def test_runner_suppresses_repeated_divider_markdown_shortcut():
    case = TestCase(
        id="DOCS-FEAT-COMP-003",
        name="插入分割线分隔两段",
        instruction="在两段之间插入一条分割线",
        expected="两段之间可见水平分割线",
        product="Docs",
        stage="docs_realistic_composition",
    )
    history = [
        StepResult(
            index=1,
            action=Action(
                kind=ActionKind.BATCH,
                sub_actions=[
                    Action(kind=ActionKind.CLICK, target="anchor end"),
                    Action(kind=ActionKind.TYPE_TEXT, text="---"),
                    Action(kind=ActionKind.HOTKEY, key="enter"),
                ],
            ),
        )
    ]
    action = Action(
        kind=ActionKind.BATCH,
        sub_actions=[
            Action(kind=ActionKind.CLICK, target="empty line"),
            Action(kind=ActionKind.TYPE_TEXT, text="---"),
            Action(kind=ActionKind.HOTKEY, key="enter"),
        ],
    )

    suppressed = _suppress_repeated_docs_divider_shortcut(case, action, history)

    assert suppressed.kind == ActionKind.WAIT
    assert suppressed.target == "divider shortcut already attempted"


def test_runner_splits_divider_focus_click_from_markdown_shortcut_batch():
    case = TestCase(
        id="DOCS-DEMO-E2E-005",
        name="插入分割线区分背景和行动",
        instruction="在两个锚点之间插入一条分割线",
        expected="两个锚点之间可见水平分割线",
        product="Docs",
        stage="docs_demo_e2e",
    )
    click = Action(kind=ActionKind.CLICK, point=None, target="end of before anchor")
    action = Action(
        kind=ActionKind.BATCH,
        target="divider insertion batch",
        sub_actions=[
            click,
            Action(kind=ActionKind.HOTKEY, key="enter"),
            Action(kind=ActionKind.TYPE_TEXT, text="---"),
            Action(kind=ActionKind.HOTKEY, key="enter"),
        ],
    )

    split = _split_docs_divider_focus_from_shortcut_batch(case, action)

    assert split.kind == ActionKind.CLICK
    assert split.target == "end of before anchor"


def test_captured_app_name_normalizes_localized_browser_name():
    assert _normal_macos_app_name("Safari浏览器") == "Safari"
    assert _normal_macos_app_name("飞书") == "飞书"


def test_single_action_allowed_list_is_enforced_like_batch_sub_action():
    case = TestCase(
        id="DOCS-FEAT-COMP-006",
        name="复制粘贴文档内局部文本",
        instruction="复制指定行",
        expected="目标处出现复制行",
        product="Docs",
        stage="docs_realistic_composition",
        allowed_actions=["click", "type_text", "hotkey", "wait", "scroll"],
    )
    action = Action(kind=ActionKind.DRAG, target="source line")

    with pytest.raises(ValueError, match="Action drag is not allowed"):
        _ensure_action_allowed(action, case)


def test_docs_rule_selection_forces_live_object_and_docs_shell():
    case = TestCase(
        id="DOCS-FEAT-FMT-001",
        name="加粗指定文本",
        instruction="打开文档，把指定文本设置为加粗",
        expected="目标文本加粗",
        product="Docs",
        stage="docs_formatting",
    )

    names = _ensure_required_rule_modules(case, ["docs_format_link"])

    assert names[:2] == ["live_object", "docs_shell"]
    assert "docs_format_link" in names


def test_docs_share_success_terminal_can_override_verifier_fail():
    case = TestCase(
        id="DOCS-P2-008",
        name="分享文档给孙浩翔",
        instruction="把当前文档分享给孙浩翔",
        expected="分享成功",
        product="Docs",
        stage="docs_share",
    )
    result = CaseResult(case=case, status=Status.PASSED)
    result.steps.append(
        StepResult(
            index=1,
            action=Action(
                kind=ActionKind.FINISHED,
                text="The document has been shared, confirmed by 修改成员权限成功 success toast.",
                thought="Visible success toast confirms permission modification.",
            ),
            passed=True,
        )
    )

    assert _accept_docs_share_success_despite_verifier_fail(result)


def test_browser_precheck_suppression_does_not_apply_to_docs_body_edit_task():
    class ScreenStub:
        suppressed = False

        def suppress_browser_precheck(self):
            self.suppressed = True

    case = TestCase(
        id="DOCS-P2-003",
        name="编辑正文短文本",
        instruction="打开“CUA-Lark Docs 测试文档 DOCS-P2-001”，在正文末尾输入内容",
        expected="正文出现内容",
        product="Docs",
        stage="docs_edit",
    )
    action = Action(kind=ActionKind.CLICK, target="document body")
    screen = ScreenStub()

    assert not _suppress_browser_precheck_action(screen, case, action, {"capture_role": "browser_precheck"})
    assert not screen.suppressed


def test_browser_precheck_suppression_blocks_docs_target_browser_search():
    class ScreenStub:
        suppressed = False

        def suppress_browser_precheck(self):
            self.suppressed = True

    case = TestCase(
        id="DOCS-FEAT-COMP-004",
        name="给局部文本添加链接",
        instruction="打开“CUA-Lark Docs Layer6 R2 Clean 20260430”，把文本设置为链接",
        expected="正文出现链接",
        product="Docs",
        stage="docs_realistic_composition",
    )
    action = Action(kind=ActionKind.CLICK, target="browser Docs search box", thought="Search for the target document from browser Docs")
    screen = ScreenStub()

    assert _suppress_browser_precheck_action(screen, case, action, {"capture_role": "browser_precheck"})
    assert screen.suppressed


def test_browser_precheck_suppression_allows_docs_target_body_edit():
    class ScreenStub:
        suppressed = False

        def suppress_browser_precheck(self):
            self.suppressed = True

    case = TestCase(
        id="DOCS-FEAT-COMP-009",
        name="搜索定位后编辑目标段",
        instruction="打开“CUA-Lark Docs Layer6 R2 Clean 20260430”，在目标段末尾追加文本",
        expected="正文出现追加文本",
        product="Docs",
        stage="docs_realistic_composition",
    )
    action = Action(kind=ActionKind.TYPE_TEXT, target="document body paragraph", text="DOCS-FEATURE-SEARCH-EDIT-DONE-0A52")
    screen = ScreenStub()

    assert not _suppress_browser_precheck_action(screen, case, action, {"capture_role": "browser_precheck"})
    assert not screen.suppressed


def test_browser_precheck_suppression_applies_to_docs_entry_case():
    class ScreenStub:
        suppressed = False

        def suppress_browser_precheck(self):
            self.suppressed = True

    case = TestCase(
        id="DOCS-ENTRY-003",
        name="从非目标文档切换到指定文档",
        instruction="从当前已经打开的另一个飞书云文档编辑页，切换到目标文档",
        expected="打开目标文档",
        product="Docs",
        stage="docs_entry_robustness",
    )
    action = Action(kind=ActionKind.CLICK, target="browser Docs search")
    screen = ScreenStub()

    assert _suppress_browser_precheck_action(screen, case, action, {"capture_role": "browser_precheck"})
    assert screen.suppressed


def test_verifier_passed_accepts_single_letter_p():
    assert _verifier_passed("P")


def test_feishu_host_activation_applies_to_calendar_but_not_docs():
    calendar_case = TestCase(
        id="CAL-DEMO-E2E-001",
        name="创建日程",
        instruction="进入飞书日历创建日程",
        expected="日程存在",
        product="Calendar",
    )
    docs_case = TestCase(
        id="DOCS-DEMO-E2E-001",
        name="打开文档",
        instruction="打开飞书云文档目标文档",
        expected="文档打开",
        product="Docs",
    )

    assert _needs_feishu_host_activation(calendar_case)
    assert not _needs_feishu_host_activation(docs_case)


def test_feishu_host_activation_infers_unknown_feishu_product_from_instruction():
    case = TestCase(
        id="GEN-001",
        name="飞书任务",
        instruction="在飞书里查看日历提醒",
        expected="看到提醒",
        product="",
    )

    assert _needs_feishu_host_activation(case)
    assert _verifier_passed("PASS")
    assert not _verifier_passed("FAIL")


def test_repeated_docs_bold_toggle_is_converted_to_finished():
    case = TestCase(
        id="DOCS-FEAT-FMT-001",
        name="加粗指定文本",
        instruction="把 DOCS-FEATURE-BOLD-TARGET-C3F7 设置为加粗",
        expected="目标文本加粗",
        product="Docs",
        stage="docs_formatting",
    )
    history = [
        StepResult(index=1, action=Action(kind=ActionKind.HOTKEY, key="command b"), passed=True),
    ]
    next_action = Action(kind=ActionKind.CLICK, target="bold B button", thought="Click bold button again")

    suppressed = _suppress_repeated_docs_bold_toggle(case, next_action, history)

    assert suppressed is not None
    assert suppressed.kind == ActionKind.HOTKEY
    assert suppressed.key == "esc"
    assert "Suppress repeated Docs bold toggle" in suppressed.thought


def test_first_docs_bold_toggle_is_not_suppressed():
    case = TestCase(
        id="DOCS-FEAT-FMT-001",
        name="加粗指定文本",
        instruction="把 DOCS-FEATURE-BOLD-TARGET-C3F7 设置为加粗",
        expected="目标文本加粗",
        product="Docs",
        stage="docs_formatting",
    )
    next_action = Action(kind=ActionKind.HOTKEY, key="command b")

    assert _suppress_repeated_docs_bold_toggle(case, next_action, []) is next_action


def test_later_docs_bold_toggle_is_suppressed_even_after_intermediate_steps():
    case = TestCase(
        id="DOCS-FEAT-FMT-001",
        name="加粗指定文本",
        instruction="把 DOCS-FEATURE-BOLD-TARGET-C3F7 设置为加粗",
        expected="目标文本加粗",
        product="Docs",
        stage="docs_formatting",
    )
    history = [
        StepResult(index=1, action=Action(kind=ActionKind.HOTKEY, key="command b"), passed=True),
        StepResult(index=2, action=Action(kind=ActionKind.CLICK, target="blank body", thought="clear selection"), passed=True),
        StepResult(index=3, action=Action(kind=ActionKind.DRAG, target="target span", thought="reselect target"), passed=True),
    ]
    next_action = Action(kind=ActionKind.CLICK, target="bold B button", thought="Click bold button again")

    suppressed = _suppress_repeated_docs_bold_toggle(case, next_action, history)

    assert suppressed is not None
    assert suppressed.kind == ActionKind.HOTKEY
    assert suppressed.key == "esc"
    assert "Suppress repeated Docs bold toggle" in suppressed.thought


def test_docs_bold_toggle_on_different_repair_target_is_not_suppressed():
    case = TestCase(
        id="DOCS-FEAT-COMP-008",
        name="只格式化句中局部短语",
        instruction="只把短语“局部高亮词-7C66”设置为加粗，不要改变同一句其他文字样式",
        expected="目标短语加粗，邻近文字普通",
        product="Docs",
        stage="docs_realistic_composition",
    )
    history = [
        StepResult(
            index=1,
            action=Action(kind=ActionKind.HOTKEY, key="command b", target='selected phrase "局部高亮词-7C66"'),
            passed=True,
        ),
    ]
    next_action = Action(kind=ActionKind.HOTKEY, key="command b", target="wrongly formatted neighboring text 需要")

    assert _suppress_repeated_docs_bold_toggle(case, next_action, history) is next_action


def test_repeated_docs_structure_insertion_click_advances_to_empty_block():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="找到 DOCS-FEATURE-TABLE-ANCHOR-3C2A，在它后面插入三列表格",
        expected="目标锚点后出现表格",
        product="Docs",
        stage="docs_realistic_composition",
    )
    history = [
        StepResult(
            index=1,
            action=Action(
                kind=ActionKind.CLICK,
                target="trailing end of DOCS-FEATURE-TABLE-ANCHOR-3C2A anchor line",
                thought="Place caret at the insertion point after the anchor line",
            ),
            passed=True,
        )
    ]
    next_action = Action(
        kind=ActionKind.CLICK,
        target="same anchor line insertion point after DOCS-FEATURE-TABLE-ANCHOR-3C2A",
        thought="Click the insertion point again because the caret is hard to see",
    )

    suppressed = _suppress_repeated_docs_structure_insertion_click(case, next_action, history)

    assert suppressed is not None
    assert suppressed.kind == ActionKind.HOTKEY
    assert suppressed.key == "enter"


def test_docs_structure_insertion_click_guard_does_not_block_table_cells():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="找到 DOCS-FEATURE-TABLE-ANCHOR-3C2A，在它后面插入三列表格",
        expected="目标锚点后出现表格",
        product="Docs",
        stage="docs_realistic_composition",
    )
    history = [
        StepResult(
            index=1,
            action=Action(
                kind=ActionKind.CLICK,
                target="trailing end of DOCS-FEATURE-TABLE-ANCHOR-3C2A anchor line",
                thought="Place caret at the insertion point after the anchor line",
            ),
            passed=True,
        ),
        StepResult(index=2, action=Action(kind=ActionKind.HOTKEY, key="enter"), passed=True),
        StepResult(index=3, action=Action(kind=ActionKind.HOTKEY, key="/"), passed=True),
    ]
    next_action = Action(
        kind=ActionKind.CLICK,
        target="second header cell of inserted 3-column table",
        thought="Click the second table cell to type the 负责人 header",
    )

    assert _suppress_repeated_docs_structure_insertion_click(case, next_action, history) is next_action
