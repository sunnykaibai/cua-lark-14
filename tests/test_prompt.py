from cua_lark.domain.models import Action, ActionKind, StepResult, TestCase
from cua_lark.testing.prompt import build_step_prompt, build_verify_prompt


def test_step_prompt_history_uses_observed_result_not_expected_text():
    case = TestCase(id="C-001", name="demo", instruction="do it", expected="hidden expected")
    step = StepResult(
        index=1,
        action=Action(
            kind=ActionKind.CLICK,
            target="search box",
            thought="click the search box",
            expected="the search box receives focus",
        ),
        passed=True,
        message="executed",
        visual_change={"status": "small-change"},
    )

    prompt = build_step_prompt(case, [step])

    assert "expected_visible_change" not in prompt
    assert "the search box receives focus" not in prompt
    assert "hidden expected" not in prompt
    assert "execution_result=executed" in prompt
    assert "observed_visual_change=small-change" in prompt


def test_step_prompt_adds_focus_stability_protocol_after_input_focus():
    case = TestCase(id="C-001", name="demo", instruction="type hello", expected="hidden expected")
    step = StepResult(
        index=1,
        action=Action(kind=ActionKind.CLICK, target="message input box", thought="click input"),
        passed=True,
        message="executed",
        visual_change={"status": "focus-likely", "raw_status": "no-visible-change"},
    )

    prompt = build_step_prompt(case, [step])

    assert "Input focus stability protocol" in prompt
    assert "caret visibility may blink" in prompt
    assert "proceed with type_text" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_input_no_change_recovery_protocol():
    case = TestCase(
        id="DOCS-ENTRY-003",
        name="从非目标文档切换到指定文档",
        instruction="从当前文档切换到目标文档",
        expected="hidden expected",
        product="Docs",
    )
    history = [
        StepResult(
            index=1,
            action=Action(kind=ActionKind.TYPE_TEXT, text="CUA-Lark Docs target"),
            passed=True,
            message="executed",
            visual_change={"status": "no-visible-change"},
        ),
        StepResult(
            index=2,
            action=Action(kind=ActionKind.TYPE_TEXT, text="CUA-Lark Docs target"),
            passed=True,
            message="executed",
            visual_change={"status": "no-visible-change"},
        ),
    ]

    prompt = build_step_prompt(case, history)

    assert "Input no-change recovery protocol" in prompt
    assert "Do not type that same text again" in prompt
    assert "refocus the visible field or clear it" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_docs_popup_close_recovery_protocol():
    case = TestCase(
        id="DOCS-SMOKE-004",
        name="打开新建文档入口",
        instruction="在飞书云文档中打开新建文档入口，进入可编辑的新文档页面",
        expected="hidden expected",
        product="Docs",
    )
    step = StepResult(
        index=1,
        action=Action(
            kind=ActionKind.CLICK,
            target="search popup close button",
            thought="Click the close X button on the search popup",
        ),
        passed=True,
        message="executed",
        visual_change={"status": "no-visible-change"},
    )

    prompt = build_step_prompt(case, [step])

    assert "Docs popup close recovery protocol" in prompt
    assert "Do not click the same close/X target again" in prompt
    assert "Prefer hotkey esc once" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_docs_insertion_focus_protocol_after_body_click():
    case = TestCase(
        id="DOCS-FEAT-EDIT-001",
        name="在指定段落后追加一句",
        instruction="打开文档，找到目标段落，在这段后追加一句 hello",
        expected="hidden expected",
        product="Docs",
        stage="docs_precise_editing",
    )
    step = StepResult(
        index=1,
        action=Action(
            kind=ActionKind.CLICK,
            target="end of target paragraph",
            thought="Click the end of the paragraph to place the cursor",
        ),
        passed=True,
        message="executed",
        visual_change={"status": "no-visible-change"},
    )

    prompt = build_step_prompt(case, [step])

    assert "Docs insertion focus protocol" in prompt
    assert "do not keep clicking the same paragraph endpoint" in prompt
    assert "Proceed with the requested type_text content" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_universal_mention_protocol():
    case = TestCase(
        id="IM-P2-006",
        name="@孙浩翔并发送消息",
        instruction="去和孙浩翔的聊天里 @孙浩翔，并发送消息",
        expected="hidden expected",
    )

    prompt = build_step_prompt(case, [])

    assert "real @ mention token" in prompt
    assert "Do not type a plain '@Name message'" in prompt
    assert "mention picker" in prompt
    assert "clear the unrelated draft first" in prompt
    assert "after a real mention token is inserted" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_minimal_feishu_host_recovery_protocol_for_calendar():
    case = TestCase(
        id="CAL-DEMO-E2E-001",
        name="创建复盘同步日程",
        instruction="从当前界面进入飞书日历并创建日程",
        expected="hidden expected",
        product="Calendar",
    )

    prompt = build_step_prompt(case, [])

    assert "recover to the Feishu host in the simplest visible way" in prompt
    assert "use that visible Feishu host as the starting point" in prompt
    assert "identify the relevant entry from the current screenshot and task" in prompt
    assert "launcher fallback such as Spotlight only when no Feishu surface is visible at all" in prompt
    assert "Do not wander through unrelated apps, web pages, or generic search results to locate Feishu" in prompt
    assert "switch to the target module" not in prompt
    assert "Look for the Feishu app sidebar or top navigation tabs" not in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_requests_multi_element_grounding():
    case = TestCase(
        id="C-001",
        name="demo",
        instruction="do it",
        expected="hidden expected",
        allowed_actions=["click", "type_text"],
    )

    prompt = build_step_prompt(case, [])

    assert "Allowed actions for this test case:" not in prompt
    assert "Action policy source:" not in prompt
    assert "per-case list is the real permission boundary" not in prompt
    assert "case allowed-action list overrides the scenario prompt and any selected rule text" not in prompt
    assert "Choose the next concrete GUI action from the scenario action vocabulary." in prompt
    assert "compact JSON Actions: line" in prompt
    assert "Always include an Action: line" in prompt
    assert "include CompletionCheck, Thought, Grounding, Action, and Expected" in prompt


def test_step_prompt_includes_selected_rules_and_docs_batch_protocol():
    case = TestCase(
        id="DOCS-BATCH-001",
        name="Docs batch trial",
        instruction="打开文档，在正文中输入 DOCS-BATCH-001",
        expected="hidden expected",
        product="Docs",
        allowed_actions=["click", "type_text", "batch"],
    )

    prompt = build_step_prompt(case, [], rules_prompt="## Rule: docs_body_edit\nUse body editor.")

    assert "Selected operation rules" in prompt
    assert "Rule: docs_body_edit" in prompt
    assert "Batch action protocol" in prompt
    assert "Every batch sub-action must also be present in this case's allowed-action list" in prompt
    assert "Docs batch trial" in prompt
    assert "Action: batch()" in prompt


def test_step_prompt_adds_marker_cleanup_finished_and_undo_protocol():
    case = TestCase(
        id="DOCS-MAINT-002",
        name="清理一级标题前的 Markdown 标记",
        instruction="删除一级标题“# DOCS-P2-005 阶段进展”前的 # 标记，保留标题样式",
        expected="正文中显示一级标题“DOCS-P2-005 阶段进展”",
        product="Docs",
        stage="docs_maintenance",
    )

    prompt = build_step_prompt(case, [])

    assert "marker-cleanup maintenance tasks" in prompt
    assert "return finished immediately" in prompt
    assert "do not switch view/edit mode" in prompt
    assert "only click near the heading and press Backspace" in prompt
    assert "use command z once" in prompt


def test_verify_prompt_accepts_rendered_marker_cleanup_in_view_mode():
    case = TestCase(
        id="DOCS-MAINT-002",
        name="清理一级标题前的 Markdown 标记",
        instruction="确保一级标题“DOCS-P2-005 阶段进展”前没有可见的“#”Markdown 标记",
        expected="正文中显示一级标题“DOCS-P2-005 阶段进展”，标题前不再显示“#”或“# ”标记",
        product="Docs",
        stage="docs_maintenance",
    )

    prompt = build_verify_prompt(case)

    assert "marker-cleanup tasks" in prompt
    assert "rendered view mode is acceptable" in prompt
    assert "visible leading '#'" in prompt


def test_step_prompt_adds_reply_operation_protocol():
    case = TestCase(
        id="IM-P2-015",
        name="回复当前会话最后一条可见真实消息",
        instruction="回复和孙浩翔聊天中最后一条可见的真实聊天消息，回复内容是“hello”",
        expected="出现带引用块的回复消息",
    )

    prompt = build_step_prompt(case, [])

    assert "real reply/reference relationship" in prompt
    assert "Do not type or send the reply text until" in prompt
    assert "do not fall back to plain sending" in prompt


def test_step_prompt_adds_search_cloud_document_share_protocol():
    case = TestCase(
        id="IM-P2-010",
        name="搜索并发送第一个可见云文档给孙浩翔",
        instruction="搜索“CUA-Lark”，把搜索结果里的第一个可见云文档分享给孙浩翔",
        expected="hidden expected",
        stage="im_attachment_share",
    )

    prompt = build_step_prompt(case, [])

    assert "Attachment and share protocol" in prompt
    assert "do not send a file path, document title, contact name, or explanation as a plain text message" in prompt
    assert "If the same result popup remains after one click" in prompt
    assert "right-side inline chain/link/share/send icon" in prompt
    assert "Do not assume the document link was copied to the clipboard" in prompt
    assert "Do not invent a more/three-dot button on a search result row" in prompt
    assert "locate that same document row in the visible cloud-document list behind it" in prompt
    assert "prefer hotkey esc" in prompt
    assert "do not reopen the same search just to select the same result again" in prompt
    assert "The next action should be hotkey esc" in prompt
    assert "use hotkey enter instead of repeatedly clicking the same result" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_personal_card_protocol():
    case = TestCase(
        id="IM-P2-020",
        name="发送个人名片给孙浩翔",
        instruction="给孙浩翔发送第一个可见个人名片",
        expected="hidden expected",
        stage="im_attachment_share",
    )

    prompt = build_step_prompt(case, [])

    assert "personal-card/contact-card option" in prompt
    assert "then send it as a card" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_docs_edit_protocol_without_im_composer_protocol():
    case = TestCase(
        id="DOCS-P2-003",
        name="编辑正文短文本",
        instruction="打开“CUA-Lark Docs 测试文档”，在正文中输入“hello”",
        expected="hidden expected",
        product="Docs",
        stage="docs_edit",
    )

    prompt = build_step_prompt(case, [])

    assert "Docs operation protocol" in prompt
    assert "body editor" in prompt
    assert "do not overwrite the document title" in prompt
    assert "do not clear the whole document" in prompt
    assert "document end" in prompt
    assert "case-id text" in prompt
    assert "prefer hotkey esc" in prompt
    assert "Composer state protocol" not in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_does_not_add_im_message_mark_protocol_for_markdown_docs():
    case = TestCase(
        id="DOCS-MD-001",
        name="追加本地 Markdown 素材",
        instruction="将本地 Markdown 素材追加到目标文档正文末尾",
        expected="hidden expected",
        product="Docs",
        stage="docs_markdown_import",
    )

    prompt = build_step_prompt(case, [])

    assert "Docs operation protocol" in prompt
    assert "Message mark protocol" not in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_includes_user_provided_input_material_without_expected():
    case = TestCase(
        id="DOCS-MD-001",
        name="追加本地 Markdown 素材",
        instruction="将本地 Markdown 素材追加到目标文档正文末尾",
        expected="hidden expected",
        product="Docs",
        stage="docs_markdown_import",
        input_materials=[
            {
                "label": "sample.md",
                "path": "/tmp/sample.md",
                "content": "# Markdown 导入视觉验证\n\nDOCS-MD-IMPORT-BEGIN-8B4D",
            }
        ],
    )

    prompt = build_step_prompt(case, [])

    assert "User-provided local input material" in prompt
    assert "sample.md" in prompt
    assert "# Markdown 导入视觉验证" in prompt
    assert "DOCS-MD-IMPORT-BEGIN-8B4D" in prompt
    assert "after visually opening the target document" in prompt
    assert "Reference token: {material:sample.md}" in prompt
    assert "do not repeat the full content in Action" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_omits_full_material_for_non_material_docs_feature_case():
    case = TestCase(
        id="DOCS-FEAT-FMT-001",
        name="加粗指定文本",
        instruction="打开文档，把文本“DOCS-FEATURE-BOLD-TARGET-C3F7”设置为加粗",
        expected="hidden expected",
        product="Docs",
        stage="docs_formatting",
        input_materials=[
            {
                "label": "docs-feature-material.md",
                "path": "/tmp/docs-feature-material.md",
                "content": "# DOCS-FEATURE-MATERIAL-ROOT-7A2D\n\nvery long material",
            }
        ],
    )

    prompt = build_step_prompt(case, [])

    assert "User-provided local input material" not in prompt
    assert "Reference token: {material:docs-feature-material.md}" not in prompt
    assert "DOCS-FEATURE-MATERIAL-ROOT-7A2D" not in prompt
    assert "very long material" not in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_docs_entry_decision_protocol():
    case = TestCase(
        id="DOCS-P2-005",
        name="插入一级标题",
        instruction="在“CUA-Lark Docs 测试文档 DOCS-P2-001”中插入一个一级标题",
        expected="hidden expected",
        product="Docs",
        stage="docs_structure",
    )

    prompt = build_step_prompt(case, [])

    assert "Entry decision protocol" in prompt
    assert "target document or required Docs state is already visible" in prompt
    assert "stay on this page and continue" in prompt
    assert "return finished immediately" in prompt
    assert "Edit mode is required only when the instruction explicitly asks" in prompt
    assert "Unified Docs entry protocol" in prompt
    assert "return to the Feishu app/Docs cloud-document entry surface" in prompt
    assert "search the exact full document title" in prompt
    assert "cloud-docs content search box/top Docs search" in prompt
    assert "do not use the far-left Feishu global search box, browser Docs home/search, or a recent-list shortcut" in prompt
    assert "use the Feishu app Docs cloud-document search area" in prompt
    assert "When switching from one already-open Docs document to a different named document" in prompt
    assert "Do not open directly from the recent list as the default route" in prompt
    assert "do not use the editor-page top-right magnifier" in prompt
    assert "visually identify and click the matching result" in prompt
    assert "wait once for navigation/loading evidence" in prompt
    assert "use Enter or another visible open affordance only if the same focused result is still present" in prompt
    assert "click a visible exact-title result before using Enter" in prompt
    assert "Prefer exact-title Docs search over browser-tab switching" in prompt
    assert "do not use browser tab switching as the primary path" in prompt
    assert "use one clear opening gesture on a visible exact-title search result" in prompt
    assert "direct recent-list row opening is fallback only" in prompt
    assert "do not open a requested document directly from a recent row by default" in prompt
    assert "use double-click on the exact title text only as fallback" in prompt
    assert "click-click-double-click loops on the same row" in prompt
    assert "prefer command f" in prompt
    assert "Do not repeatedly click the top-right global search icon" in prompt
    assert "merely depicted inside the document body" in prompt
    assert "treat it as embedded document content" in prompt
    assert "Do not click browser tabs, system menu icons, app icons, or browser chrome" in prompt
    assert "exact requested target document title" in prompt
    assert "do not use browser Docs home/search as the default route" in prompt
    assert "dropdown, menu, share dialog, or permission panel blocks the document" in prompt
    assert "do not repeat the same click" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_prefers_browser_host_for_docs_content_changes():
    case = TestCase(
        id="DOCS-FEAT-COMP-004",
        name="给局部文本添加链接",
        instruction="打开“CUA-Lark Docs 测试文档 DOCS-P2-001”，把文本“DOCS-FEATURE-LINK-TARGET-8A41”设置为链接",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_step_prompt(case, [])

    assert "Browser execution host protocol" in prompt
    assert "preferred editing host is the browser Docs page" in prompt
    assert "do not start editing directly there" in prompt
    assert "search the exact full title" in prompt
    assert "wait for browser handoff before editing" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_does_not_force_browser_host_for_docs_provision():
    case = TestCase(
        id="DOCS-R2-L6-CLEAN-PROVISION-001",
        name="创建 Layer6 R2 干净测试文档并导入素材",
        instruction="在飞书云文档中新建一个文档，标题设为“CUA-Lark Docs Layer6 R2 Clean 20260430”，然后在正文中粘贴本地 Markdown 素材",
        expected="hidden expected",
        product="Docs",
        stage="docs_r2_layer6_clean_provision",
    )

    prompt = build_step_prompt(case, [])

    assert "Provision/create host protocol" in prompt
    assert "Do not open a browser new tab" in prompt
    assert "Browser execution host protocol" not in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_docs_entry_repeat_stop_protocol():
    case = TestCase(
        id="DOCS-ENTRY-003",
        name="从非目标文档切换到指定文档",
        instruction="从当前已经打开的另一个飞书云文档编辑页，切换到“CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET”",
        expected="hidden expected",
        product="Docs",
        stage="docs_entry_robustness",
    )
    history = [
        StepResult(
            index=1,
            action=Action(
                kind=ActionKind.CLICK,
                target="exact-title document search result",
                thought="Click the matching document search result title",
            ),
            passed=True,
            message="executed",
            visual_change={"status": "small-change"},
        ),
        StepResult(
            index=2,
            action=Action(
                kind=ActionKind.CLICK,
                target="exact-title document search result",
                thought="Click the matching document search result title again",
            ),
            passed=True,
            message="executed",
            visual_change={"status": "no-visible-change"},
        ),
    ]

    prompt = build_step_prompt(case, history)

    assert "Docs entry repeat-stop protocol" in prompt
    assert "return finished immediately" in prompt
    assert "do not click that same result again" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_docs_structure_prefers_visible_block_type_control():
    case = TestCase(
        id="DOCS-FEAT-FMT-004",
        name="将普通段落转成标题或列表",
        instruction="把包含目标标识的普通段落转换成标题或列表",
        expected="hidden expected",
        product="Docs",
        stage="docs_formatting",
    )

    prompt = build_step_prompt(case, [])

    assert "nearby block type control" in prompt
    assert "T icon" in prompt
    assert "Do not invent unverified heading shortcuts" in prompt
    assert "command shift 1" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_docs_table_fallback_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="插入三列表格",
        instruction="在目标锚点后插入一个三列表格",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_step_prompt(case, [])

    assert "For table tasks" in prompt
    assert "at most once" in prompt
    assert "do not keep typing more slash text" in prompt
    assert "Do not rely on Markdown table text to auto-convert" in prompt
    assert "plain-text table" in prompt
    assert "rendered table grid" in prompt
    assert "close any open find/search popup, floating toolbar" in prompt
    assert "insert menu, or transient panel" in prompt
    assert "true empty body block" in prompt
    assert "After clicking the trailing end of the anchor line once" in prompt
    assert "hotkey(key='/')" in prompt
    assert "Do not use type_text('/')" in prompt
    assert "top-right 编辑/修订/阅读 mode dropdown" in prompt
    assert "floating toolbar, an insert menu, or another transient UI has focus" in prompt
    assert "Do not type '表格' unless a slash menu/search field is visibly open" in prompt
    assert "immediately clear that literal '/'" in prompt
    assert "visible toolbar, block-type, insert, table, list, or divider control path" in prompt
    assert "Do not use the top-right global '+'" in prompt
    assert "fill cells in reading order" in prompt
    assert "Do not press Enter to move between table cells" in prompt
    assert "do not type the same header or row value twice" in prompt
    assert "stacked as two text lines inside the same table cell is not a valid two-row table" in prompt
    assert "`事项` appears directly above `素材复核`" in prompt
    assert "The empty row below does not make that a valid data row" in prompt
    assert "move the data values into the empty row cells" in prompt
    assert "Count populated table ROWS, not text lines" in prompt
    assert "one populated row whose cells contain both header and data text, followed by a blank row" in prompt
    assert "do not return finished as the first action" in prompt
    assert "Dirty stacked-table repair sequence" in prompt
    assert "Do not reopen document find/search after selecting a wrongly stacked data value" in prompt
    assert "A double-click on a wrongly stacked data value is only selection, not repair" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_docs_structure_insertion_click_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="插入三列表格",
        instruction="在目标锚点后插入一个三列表格",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )
    history = [
        StepResult(
            index=1,
            action=Action(
                kind=ActionKind.CLICK,
                target="trailing end of DOCS-FEATURE-TABLE-ANCHOR-3C2A line",
                thought="Click right after the anchor line to place the cursor at the insertion point",
            ),
            visual_change={"status": "small-change"},
        )
    ]

    prompt = build_step_prompt(case, history)

    assert "Docs structure insertion-point protocol" in prompt
    assert "do not repeat that same insertion-point click" in prompt
    assert "hotkey enter or shift enter" in prompt
    assert "It should not be another click on the same line end" in prompt


def test_step_prompt_adds_docs_slash_repeat_stop_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="插入三列表格",
        instruction="在目标锚点后插入一个三列表格",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )
    history = [
        StepResult(index=1, action=Action(kind=ActionKind.TYPE_TEXT, text="/", thought="type slash")),
        StepResult(index=2, action=Action(kind=ActionKind.TYPE_TEXT, text="表格", thought="type table keyword")),
    ]

    prompt = build_step_prompt(case, history)

    assert "Docs slash-command repeat-stop protocol" in prompt
    assert "Do not type '/', '/表格', '/table', '/分割线'" in prompt
    assert "not the browser tab/new-page plus" in prompt


def test_step_prompt_adds_docs_divider_finish_when_visible_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-003",
        name="插入分割线分隔两段",
        instruction="在 DOCS-FEATURE-DIVIDER-BEFORE-6B70 和 DOCS-FEATURE-DIVIDER-AFTER-6B70 之间插入一条分割线",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_step_prompt(case, [])

    assert "return finished as soon as a rendered horizontal divider is visible" in prompt
    assert "thin gray horizontal line counts as divider evidence" in prompt
    assert "do not batch the anchor/insertion click together with typing `---`" in prompt
    assert "do not type `---` again on the next step" in prompt
    assert "no obvious extra blank paragraph inserted below it" in prompt
    assert "type `---`, then press Enter once" in prompt
    assert "do not scroll that menu more than once" in prompt
    assert "Do not click the divider area" in prompt
    assert "find popup, red search highlight, or caret" in prompt


def test_step_prompt_adds_docs_heading_toc_sidebar_disambiguation():
    case = TestCase(
        id="DOCS-FEAT-COMP-011",
        name="新建标题并用目录定位",
        instruction="新增二级标题 DOCS-FEATURE-HEADING-TOC-NEW-A0D8，然后借助文档目录定位到这个新标题",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_step_prompt(case, [])

    assert "The document outline/目录 is not the global Feishu file/navigation sidebar" in prompt
    assert "主页, 云盘, 知识库" in prompt
    assert "open the document's own 目录/outline panel instead" in prompt
    assert "Do not repeatedly scroll the global sidebar" in prompt


def test_step_prompt_adds_docs_structure_after_find_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="插入三列表格",
        instruction="在目标锚点后插入一个三列表格",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )
    history = [
        StepResult(index=1, action=Action(kind=ActionKind.HOTKEY, key="command f")),
        StepResult(index=2, action=Action(kind=ActionKind.TYPE_TEXT, text="DOCS-FEATURE-TABLE-ANCHOR-3C2A")),
    ]

    prompt = build_step_prompt(case, history)

    assert "Docs structure-after-find protocol" in prompt
    assert "close the find/search panel with hotkey esc once" in prompt
    assert "after the full sentence including final punctuation" in prompt


def test_step_prompt_docs_divider_plain_text_recovery_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-003",
        name="插入分割线分隔两段",
        instruction="在两段之间插入一条分割线",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_step_prompt(case, [])

    assert "typed `/分割线` or `/divider` text is only a trigger" in prompt
    assert "plain text remains after the trigger" in prompt
    assert "rendered horizontal divider" in prompt


def test_step_and_verify_prompt_add_docs_link_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-004",
        name="给局部文本添加链接",
        instruction="把文本设置为链接，链接地址使用 https://example.com/demo",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    step_prompt = build_step_prompt(case, [])
    verify_prompt = build_verify_prompt(case)

    assert "return finished immediately" in step_prompt
    assert "Do not reopen the link dialog repeatedly" in step_prompt
    assert "Standard link path" in step_prompt
    assert "command k or the visible link icon" in step_prompt
    assert "next action should confirm it with Enter" in step_prompt
    assert "Do not click a link confirm/apply button before entering" in step_prompt
    assert "selected blue" in verify_prompt
    assert "URL popup is useful but not required" in verify_prompt
    assert "hidden expected" not in step_prompt


def test_verify_prompt_rejects_dirty_divider_extra_blank_or_selection():
    case = TestCase(
        id="DOCS-DEMO-E2E-005",
        name="插入分割线区分背景和行动",
        instruction="在两个锚点之间插入一条分割线",
        expected="两个锚点之间出现横向分割线",
        product="Docs",
        stage="docs_demo_e2e",
    )

    prompt = build_verify_prompt(case)

    assert "exactly one rendered divider" in prompt
    assert "no obvious extra blank editable paragraph" in prompt
    assert "blue selected empty block" in prompt


def test_step_prompt_docs_comment_prefers_floating_toolbar_not_right_click():
    case = TestCase(
        id="DOCS-DEMO-E2E-006",
        name="给后续行动添加评论",
        instruction="选中“DOCS-DEMO-TODO-TODO-20260506”，给它添加评论“请确认会议时间”",
        expected="指定文本旁出现评论",
        product="Docs",
        stage="docs_demo_e2e",
    )

    prompt = build_step_prompt(case, [])

    assert "use the visible comment/speech-bubble icon" in prompt
    assert "Do not use right-click as the normal comment path" in prompt
    assert "do not repeat drag-selection" in prompt


def test_step_prompt_adds_docs_undo_redo_protocol():
    case = TestCase(
        id="DOCS-FEAT-EDIT-004",
        name="撤销并重做一次编辑",
        instruction="在目标段落后新增 hello，然后撤销这次新增，再重做恢复它",
        expected="hidden expected",
        product="Docs",
        stage="docs_precise_editing",
    )

    prompt = build_step_prompt(case, [])

    assert "For undo/redo tasks" in prompt
    assert "command z" in prompt
    assert "command shift z" in prompt
    assert "Do not type the same requested text again as a substitute for redo" in prompt
    assert "hidden expected" not in prompt


def test_step_and_verify_prompt_add_docs_task_list_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-013",
        name="插入任务列表并保留未完成项",
        instruction="在目标后插入任务列表，一项未完成，一项已完成",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    step_prompt = build_step_prompt(case, [])
    verify_prompt = build_verify_prompt(case)

    assert "real checkbox/task items" in step_prompt
    assert "do not choose divider/separator/分割线" in step_prompt
    assert "A divider is wrong output for a checklist task" in step_prompt
    assert "visible options named 待办, 任务, 任务列表, checklist, or checkbox" in step_prompt
    assert "Keep the requested open item unchecked" in step_prompt
    assert "done item has a checked/completed visual style" in step_prompt
    assert "plain markdown markers like '[ ]'" in verify_prompt
    assert "hidden expected" not in step_prompt


def test_step_and_verify_prompt_add_docs_move_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-007",
        name="移动段落到另一段之前",
        instruction="把整段 source 移动到 target 段落之前",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    step_prompt = build_step_prompt(case, [])
    verify_prompt = build_verify_prompt(case)

    assert "move the existing source paragraph" in step_prompt
    assert "do not type a duplicate source paragraph" in step_prompt
    assert "0 matches for the source paragraph" in step_prompt
    assert "shared test document as dirty" in step_prompt
    assert "source is already directly before the target paragraph" in step_prompt
    assert "source paragraph is visibly before the target paragraph" in verify_prompt
    assert "duplicated instead of moved" in verify_prompt
    assert "hidden expected" not in step_prompt


def test_step_prompt_adds_docs_move_dirty_recovery_after_zero_match():
    case = TestCase(
        id="DOCS-FEAT-COMP-007",
        name="移动段落到另一段之前",
        instruction="把整段 source 移动到 target 段落之前",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )
    step = StepResult(
        index=1,
        action=Action(
            kind=ActionKind.CLICK,
            target="Find panel close button",
            thought="Click close because find reports 0 matches for the source paragraph",
        ),
        passed=True,
        message="executed",
        visual_change={"status": "no-visible-change"},
    )

    prompt = build_step_prompt(case, [step])

    assert "Docs move dirty-data recovery protocol" in prompt
    assert "Do not search, scroll, or infer" in prompt
    assert "focus immediately before the visible target paragraph" in prompt
    assert "type the exact source paragraph once followed by Enter" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_heading_toc_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-011",
        name="新建标题并用目录定位",
        instruction="新增二级标题 hello，然后借助文档目录定位到这个新标题",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_step_prompt(case, [])

    assert "choose heading 2" in prompt
    assert "literal markdown prefix like '## '" in prompt
    assert "heading plus outline" in prompt
    assert "visible outline/目录 button" in prompt
    assert "return finished instead of retyping" in prompt
    assert "hidden expected" not in prompt


def test_step_and_verify_prompt_add_partial_format_cleanup_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-008",
        name="只格式化句中局部短语",
        instruction="只把短语“局部高亮词-7C66”设置为高亮或加粗，不要改变同一句其他文字样式",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    step_prompt = build_step_prompt(case, [])
    verify_prompt = build_verify_prompt(case)

    assert "For partial phrase formatting tasks" in step_prompt
    assert "wrongly formatted neighboring text" in step_prompt
    assert "repair target is the extra formatted neighbor" in step_prompt
    assert "close any find/search panel" in step_prompt
    assert "search-result highlighting is not confused" in step_prompt
    assert "surrounding words in the same sentence remain ordinary" in step_prompt
    assert "not selected or highlighted by an open find panel" in step_prompt
    assert "Do not count transient find/search result tinting" in verify_prompt
    assert "hidden expected" not in step_prompt


def test_step_prompt_adds_docs_bold_toggle_guard():
    case = TestCase(
        id="DOCS-FEAT-FMT-001",
        name="加粗指定文本",
        instruction="把文本“DOCS-FEATURE-BOLD-TARGET-C3F7”设置为加粗",
        expected="hidden expected",
        product="Docs",
        stage="docs_formatting",
    )

    step_prompt = build_step_prompt(case, [])

    assert "Docs bold is a toggle" in step_prompt
    assert "First judge whether" in step_prompt
    assert "apply bold with one method only" in step_prompt
    assert "already appears visibly bold" in step_prompt
    assert "toggle bold back off" in step_prompt
    assert "Use at most one bold toggle total per exact target span" in step_prompt
    assert "do not guess from a selected or search-highlighted state" in step_prompt
    assert "Never use a second bold toggle" in step_prompt
    assert "clear transient selection or find/search highlighting" in step_prompt
    assert "do not treat a visible selection as a valid final state" in step_prompt
    assert "hidden expected" not in step_prompt


def test_step_and_verify_prompt_require_full_local_md_agenda_visibility():
    case = TestCase(
        id="DOCS-FEAT-COMP-014",
        name="从本地 Markdown 局部复制粘贴议程",
        instruction="从本地 Markdown 素材中只复制议程片段，粘贴到目标锚点后，包含“同步目标”和“确认风险”",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    step_prompt = build_step_prompt(case, [])
    verify_prompt = build_verify_prompt(case)

    assert "all requested bullet lines are already visible" in step_prompt
    assert "Scroll slightly down until both requested agenda bullets" in step_prompt
    assert "PASS only if the requested bounded snippet content is visible" in verify_prompt
    assert "FAIL if only the heading or only one agenda bullet is visible" in verify_prompt
    assert "Do not count the original bounded snippet in the source material section as success" in verify_prompt
    assert "wrong version and a correct version are visible" in verify_prompt
    assert "hidden expected" not in step_prompt


def test_step_prompt_adds_local_markdown_self_repair_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-014",
        name="从本地 Markdown 局部复制粘贴议程",
        instruction="从本地 Markdown 素材中读取议程片段，并导入为飞书文档结构，包含标题和项目符号列表",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_step_prompt(case, [])

    assert "Feishu Docs may paste Markdown as raw text instead of rendering it" in prompt
    assert "deleting only the leading marker and following space" in prompt
    assert "preserving the title text" in prompt
    assert "removing only the literal '- ' prefixes" in prompt
    assert "visible bullet-list/list control" in prompt
    assert "Markdown pipe table remains as literal text" in prompt
    assert "Insert a real Docs table/grid" in prompt
    assert "duplicate wrong versions remain near the target anchor" in prompt


def test_verify_prompt_docs_table_rejects_literal_markdown_table_and_slash_residue():
    case = TestCase(
        id="DOCS-FEAT-COMP-015",
        name="从本地 Markdown 局部复制粘贴表格",
        instruction="从本地 Markdown 素材中复制小表格，粘贴到锚点后",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_verify_prompt(case)

    assert "literal Markdown pipe text" in prompt
    assert "literal slash-command text" in prompt
    assert "wrong-version residue" in prompt
    assert "stacked as multiple text lines inside the same table cells" in prompt
    assert "horizontal row boundary must separate the header row from the data row" in prompt
    assert "Specifically FAIL the bad pattern where `事项` is directly above `素材复核`" in prompt
    assert "empty row below those cells does not count" in prompt


def test_verify_prompt_blocks_docs_body_text_in_title_area():
    case = TestCase(
        id="DOCS-P2-003",
        name="编辑正文短文本",
        instruction="打开文档，在正文末尾输入“DOCS-P2-003 正文编辑验证”",
        expected="hidden expected",
        product="Docs",
        stage="docs_edit",
    )

    prompt = build_verify_prompt(case)

    assert "Docs verification protocol" in prompt
    assert "below the title and author/modified metadata" in prompt
    assert "appended to, merged into, or primarily displayed in the document title" in prompt
    assert "document title is visibly polluted" in prompt


def test_step_prompt_docs_title_creation_does_not_add_im_attachment_or_structure_protocols():
    case = TestCase(
        id="DOCS-P2-001",
        name="创建测试文档并设置标题",
        instruction="在飞书云文档中新建一个文档，标题设为“CUA-Lark Docs 测试文档”",
        expected="hidden expected",
        product="Docs",
        stage="docs_create",
    )

    prompt = build_step_prompt(case, [])

    assert "Docs operation protocol" in prompt
    assert "Ignore browser chrome" in prompt
    assert "For explicit new-document creation tasks, do not search for an existing same-title document first" in prompt
    assert "target the title field specifically" in prompt
    assert "do not click any create/new button again" in prompt
    assert "Attachment and share protocol" not in prompt
    assert "slash commands" not in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_docs_create_waits_for_loading_after_blank_doc_card():
    case = TestCase(
        id="DOCS-SMOKE-004",
        name="打开新建文档入口",
        instruction="在飞书云文档中打开新建文档入口，进入可编辑的新文档页面",
        expected="hidden expected",
        product="Docs",
        stage="docs_editor_smoke",
        allowed_actions=["click", "wait"],
    )

    prompt = build_step_prompt(case, [])

    assert "After selecting a blank/new document card" in prompt
    assert "创建中" in prompt
    assert "return finished for open-new-document smoke tasks" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_docs_share_protocol():
    case = TestCase(
        id="DOCS-P2-008",
        name="分享文档给孙浩翔",
        instruction="把当前“CUA-Lark Docs 测试文档”分享给孙浩翔",
        expected="hidden expected",
        product="Docs",
        stage="docs_share",
    )

    prompt = build_step_prompt(case, [])

    assert "Docs operation protocol" in prompt
    assert "visible Share/分享 workflow" in prompt
    assert "already visible in the collaborator/permission list" in prompt
    assert "do not send a new invitation" not in prompt
    assert "Do not copy a hidden link" in prompt
    assert "Composer state protocol" not in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_adds_docs_share_inspect_protocol():
    case = TestCase(
        id="DOCS-P2-009",
        name="检查文档分享入口和权限状态",
        instruction="打开“CUA-Lark Docs 测试文档”的分享入口，查看当前分享或权限状态",
        expected="hidden expected",
        product="Docs",
        stage="docs_share",
    )

    prompt = build_step_prompt(case, [])

    assert "inspect sharing state" in prompt
    assert "must not send a new invitation" in prompt
    assert "hidden expected" not in prompt


def test_step_prompt_applies_docs_host_precondition_to_all_editing_cases():
    case = TestCase(
        id="DOCS-FEAT-EDIT-002",
        name="替换指定词语",
        instruction="把文本“蓝色信标”改成“青色信标”",
        expected="hidden expected",
        product="Docs",
        stage="docs_precise_editing",
    )

    prompt = build_step_prompt(case, [])

    assert "This applies even when the instruction does not name a document title" in prompt
    assert "Recover to Feishu app -> 云文档/Docs first" in prompt


def test_step_prompt_prefers_matching_same_title_snippet_when_multiple_results_exist():
    case = TestCase(
        id="DOCS-FEAT-FMT-001",
        name="加粗指定文本",
        instruction="打开“CUA-Lark Docs 测试文档 DOCS-P2-001”，把文本“DOCS-FEATURE-BOLD-TARGET-C3F7”设置为加粗",
        expected="hidden expected",
        product="Docs",
        stage="docs_formatting",
    )

    prompt = build_step_prompt(case, [])

    assert "If multiple exact-title search results are visible" in prompt
    assert "best matches the current case's unique anchor" in prompt


def test_step_prompt_adds_docs_exact_span_protocol():
    case = TestCase(
        id="DOCS-FEAT-COMP-004",
        name="给局部文本添加链接",
        instruction="打开文档，把文本“DOCS-FEATURE-LINK-TARGET-8A41：目标”设置为链接",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_step_prompt(case, [])

    assert "Exact-span operation protocol" in prompt
    assert "every requested character is included" in prompt
    assert "Chinese/English punctuation" in prompt
    assert "Anchor insertion-point protocol" in prompt
    assert "Do not insert before the final punctuation mark" in prompt
    assert "trailing punctuation of the anchor appears alone on the next line" in prompt
    assert "Do not select the whole sentence" in prompt
    assert "clear transient find/search highlights" in prompt


def test_verify_prompt_checks_docs_exact_span_boundaries():
    case = TestCase(
        id="DOCS-FEAT-COMP-008",
        name="只格式化句中局部短语",
        instruction="打开文档，只格式化局部短语“风险：A-17”",
        expected="hidden expected",
        product="Docs",
        stage="docs_realistic_composition",
    )

    prompt = build_verify_prompt(case)

    assert "exact-span local text operations" in prompt
    assert "including punctuation" in prompt
    assert "missed punctuation" in prompt
    assert "neighboring text" in prompt
    assert "floating toolbar" in prompt


def test_verify_prompt_accepts_docs_share_success_toasts():
    case = TestCase(
        id="DOCS-P2-008",
        name="分享文档给孙浩翔",
        instruction="把当前文档分享给孙浩翔",
        expected="hidden expected",
        product="Docs",
        stage="docs_share",
    )

    prompt = build_verify_prompt(case)

    assert "visible success toast confirming invitation/share/permission modification" in prompt
    assert "邀请成员成功" in prompt
    assert "修改成员权限成功" in prompt
    assert "Do not require the recipient name to remain visible" in prompt
    assert "hidden expected" in prompt


def test_step_and_verify_prompt_stops_after_visible_structured_heading():
    case = TestCase(
        id="DOCS-P2-005",
        name="插入一级标题",
        instruction="在文档中插入一个一级标题“DOCS-P2-005 阶段进展”",
        expected="hidden expected",
        product="Docs",
        stage="docs_structure",
    )

    step_prompt = build_step_prompt(case, [])
    verify_prompt = build_verify_prompt(case)

    assert "After one clear structure insertion attempt" in step_prompt
    assert "Do not repeatedly click, type spaces, backspace, or toggle edit mode" in step_prompt
    assert "return finished and let the verifier judge" in step_prompt
    assert "do not fail solely because a markdown marker is still visible" in verify_prompt


def test_step_prompt_adds_rich_text_protocol():
    case = TestCase(
        id="IM-P2-023",
        name="发送加粗格式文本给孙浩翔",
        instruction="给孙浩翔发送一条加粗消息“CUA-Lark 加粗格式测试 023”",
        expected="hidden expected",
        stage="im_cross_view",
    )

    prompt = build_step_prompt(case, [])

    assert "Rich text protocol" in prompt
    assert "visible bold B control" in prompt
    assert "return finished instead of clicking the composer and typing the same text again" in prompt
    assert "hidden expected" not in prompt
