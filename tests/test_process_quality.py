from cua_lark.domain.models import Action, ActionKind, CaseResult, Status, StepResult, TestCase
from cua_lark.testing.process_quality import evaluate_process_quality


def test_process_quality_flags_dirty_mention_path():
    case = TestCase(
        id="IM-P2-006",
        name="@孙浩翔并发送消息",
        instruction="去和孙浩翔的聊天里 @孙浩翔，并发送消息",
        expected="包含 @孙浩翔",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.TYPE_TEXT, text="@孙浩翔 hello")),
            StepResult(index=2, action=Action(kind=ActionKind.HOTKEY, key="enter")),
            StepResult(index=3, action=Action(kind=ActionKind.HOTKEY, key="enter")),
            StepResult(
                index=4,
                action=Action(
                    kind=ActionKind.CLICK,
                    target="@ button in the chat input toolbar",
                    grounding_check={"changed_point": True},
                ),
            ),
            StepResult(index=5, action=Action(kind=ActionKind.CLICK, target="孙浩翔 option in @ mention pop-up")),
        ],
    )

    quality = evaluate_process_quality(result)

    assert quality["status"] == "warning"
    assert "multiple_enter_sends:2" in quality["warnings"]
    assert "plain_at_text_inputs:1" in quality["warnings"]
    assert "grounding_corrected:1" in quality["warnings"]
    assert quality["mention_button_observed"] is True
    assert quality["mention_option_observed"] is True


def test_process_quality_allows_real_mention_picker_path():
    case = TestCase(
        id="IM-P2-006",
        name="@孙浩翔并发送消息",
        instruction="去和孙浩翔的聊天里 @孙浩翔，并发送消息",
        expected="包含 @孙浩翔",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.CLICK, target="chat message input box")),
            StepResult(index=2, action=Action(kind=ActionKind.TYPE_TEXT, text="@")),
            StepResult(index=3, action=Action(kind=ActionKind.CLICK, target="孙浩翔 mention option in the dropdown")),
            StepResult(index=4, action=Action(kind=ActionKind.TYPE_TEXT, text=" CUA-Lark Phase2 @提及 006")),
            StepResult(index=5, action=Action(kind=ActionKind.HOTKEY, key="enter")),
        ],
    )

    quality = evaluate_process_quality(result)

    assert quality["status"] == "clean"
    assert quality["plain_at_text_input_count"] == 0


def test_process_quality_blocks_plain_reply_send():
    case = TestCase(
        id="IM-P2-015",
        name="回复当前会话最后一条可见真实消息",
        instruction="回复最后一条消息",
        expected="带引用关系的新回复消息",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.CLICK, target="chat input box")),
            StepResult(index=2, action=Action(kind=ActionKind.TYPE_TEXT, target="chat input box", text="hello")),
            StepResult(index=3, action=Action(kind=ActionKind.HOTKEY, target="chat input box", key="enter")),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "reply_without_reference_operation" in quality["blocking_warnings"]


def test_process_quality_allows_reply_context_menu_path():
    case = TestCase(
        id="IM-P2-015",
        name="回复当前会话最后一条可见真实消息",
        instruction="回复最后一条消息",
        expected="带引用关系的新回复消息",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.RIGHT_CLICK, target="last real message bubble")),
            StepResult(index=2, action=Action(kind=ActionKind.CLICK, target="回复 menu option")),
            StepResult(index=3, action=Action(kind=ActionKind.TYPE_TEXT, target="reply composer", text="hello")),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "reply_without_reference_operation" not in quality["blocking_warnings"]


def test_process_quality_blocks_cloud_share_clipboard_paste():
    case = TestCase(
        id="IM-P2-010",
        name="搜索并发送第一个可见云文档给孙浩翔",
        instruction="搜索“CUA-Lark”，把搜索结果里的第一个可见云文档分享给孙浩翔",
        expected="云文档卡片",
        stage="im_attachment_share",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.HOTKEY,
                    key="command v",
                    target="孙浩翔 chat message input box",
                    thought="Paste copied cloud document link",
                ),
            )
        ],
    )

    quality = evaluate_process_quality(result)

    assert "cloud_share_clipboard_paste" in quality["blocking_warnings"]


def test_process_quality_blocks_docs_duplicate_body_text_input():
    case = TestCase(
        id="DOCS-P2-003",
        name="编辑正文短文本",
        instruction="打开文档，在正文末尾输入“DOCS-P2-003 正文编辑验证”",
        expected="正文出现目标文本",
        product="Docs",
        stage="docs_edit",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.CLICK, target="document body editor")),
            StepResult(index=2, action=Action(kind=ActionKind.TYPE_TEXT, target="document body editor", text="DOCS-P2-003 正文编辑验证")),
            StepResult(index=3, action=Action(kind=ActionKind.TYPE_TEXT, target="document body editor", text="DOCS-P2-003 正文编辑验证")),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_duplicate_exact_body_text_input" in quality["blocking_warnings"]


def test_process_quality_allows_reusing_title_text_for_search_and_title_field():
    case = TestCase(
        id="DOCS-R2-L6-CLEAN-PROVISION-001",
        name="创建 Layer6 R2 干净测试文档并导入素材",
        instruction="新建文档，标题设为“CUA-Lark Docs Layer6 R2 Clean 20260430”，然后在正文中粘贴素材",
        expected="正文包含素材",
        product="Docs",
        stage="docs_r2_layer6_clean_provision",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.TYPE_TEXT, target="cloud docs search input", text="CUA-Lark Docs Layer6 R2 Clean 20260430")),
            StepResult(index=2, action=Action(kind=ActionKind.TYPE_TEXT, target="document title input field", text="CUA-Lark Docs Layer6 R2 Clean 20260430")),
            StepResult(index=3, action=Action(kind=ActionKind.TYPE_TEXT, target="body editor area", text="DOCS-FEATURE-MATERIAL-ROOT-7A2D")),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_duplicate_exact_body_text_input" not in quality["blocking_warnings"]


def test_process_quality_blocks_docs_body_click_near_title_area():
    case = TestCase(
        id="DOCS-P2-003",
        name="编辑正文短文本",
        instruction="打开文档，在正文末尾输入“DOCS-P2-003 正文编辑验证”",
        expected="正文出现目标文本",
        product="Docs",
        stage="docs_edit",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.CLICK,
                    target="document body editor",
                    grounding={"box_0_1000": [336, 289, 537, 326], "point_0_1000": [432, 308]},
                ),
            )
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_body_click_may_target_title_area" in quality["blocking_warnings"]


def test_process_quality_allows_docs_body_click_box_extending_below_title_area():
    case = TestCase(
        id="DOCS-P2-004",
        name="追加第二段正文",
        instruction="在文档正文末尾另起一段",
        expected="正文出现目标文本",
        product="Docs",
        stage="docs_edit",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.CLICK,
                    target="empty body area below existing text",
                    grounding={"box_0_1000": [333, 320, 650, 450], "point_0_1000": [354, 352]},
                ),
            )
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_body_click_may_target_title_area" not in quality["blocking_warnings"]


def test_process_quality_allows_docs_body_placeholder_near_top():
    case = TestCase(
        id="DOCS-P2-003",
        name="编辑正文短文本",
        instruction="打开文档，在正文末尾输入“DOCS-P2-003 正文编辑验证”",
        expected="正文出现目标文本",
        product="Docs",
        stage="docs_edit",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.CLICK,
                    target="body editor placeholder",
                    thought="Click the body editor placeholder below the author metadata",
                    grounding={"box_0_1000": [239, 300, 432, 320], "point_0_1000": [286, 306]},
                ),
            )
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_body_click_may_target_title_area" not in quality["blocking_warnings"]


def test_process_quality_allows_docs_anchor_paragraph_click_near_top_viewport():
    case = TestCase(
        id="DOCS-FEAT-EDIT-001",
        name="在指定段落后追加一句",
        instruction="打开文档，找到包含锚点的段落，在这段后追加一句",
        expected="正文出现目标文本",
        product="Docs",
        stage="docs_precise_editing",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.CLICK,
                    target="end of target paragraph in document body",
                    thought="Click the end of the DOCS-FEATURE-ANCHOR paragraph",
                    grounding={"box_0_1000": [421, 226, 744, 268], "point_0_1000": [432, 263]},
                ),
            )
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_body_click_may_target_title_area" not in quality["blocking_warnings"]


def test_process_quality_allows_last_body_line_click_near_top_viewport():
    case = TestCase(
        id="DOCS-P2-003",
        name="编辑正文短文本",
        instruction="打开文档，在正文末尾输入“DOCS-P2-003 正文编辑验证”",
        expected="正文出现目标文本",
        product="Docs",
        stage="docs_edit",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.CLICK,
                    target="end of last document body line",
                    thought="Click the end of the last document body line after old content.",
                    grounding={"box_0_1000": [421, 226, 744, 268], "point_0_1000": [600, 263]},
                ),
            )
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_body_click_may_target_title_area" not in quality["blocking_warnings"]


def test_process_quality_allows_document_body_end_click_near_top_viewport():
    case = TestCase(
        id="DOCS-FEAT-PREP-001",
        name="导入 Docs 深水区功能素材",
        instruction="把本地 Markdown 素材追加到正文末尾",
        expected="正文出现素材根标识",
        product="Docs",
        stage="docs_feature_prep",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.CLICK,
                    target="Document body end empty area",
                    thought="Click the document body end insertion point.",
                    grounding={"box_0_1000": [332, 280, 612, 330], "point_0_1000": [500, 314]},
                ),
            )
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_body_click_may_target_title_area" not in quality["blocking_warnings"]


def test_process_quality_allows_multiple_enters_for_docs_list_creation():
    case = TestCase(
        id="DOCS-P2-006",
        name="插入项目符号列表",
        instruction="在文档中插入项目符号列表",
        expected="出现三项列表",
        product="Docs",
        stage="docs_structure",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.HOTKEY, key="enter")),
            StepResult(index=2, action=Action(kind=ActionKind.HOTKEY, key="enter")),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "multiple_enter_sends:2" not in quality["warnings"]


def test_process_quality_warns_when_final_verify_passes_after_failed_step():
    case = TestCase(
        id="DOCS-ENTRY-006",
        name="打开指定文档",
        instruction="打开目标文档",
        expected="目标文档可见",
        product="Docs",
        stage="docs_entry_robustness",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.CLICK, target="search result"), passed=True),
            StepResult(index=2, action=Action(kind=ActionKind.CLICK, target="search result"), passed=False, message="capture failed"),
        ],
    )

    quality = evaluate_process_quality(result)

    assert quality["status"] == "warning"
    assert "failed_steps_present:1" in quality["warnings"]


def test_process_quality_blocks_accidental_full_material_paste_in_non_material_docs_case():
    case = TestCase(
        id="DOCS-FEAT-COMP-002",
        name="创建待办清单并勾选一项",
        instruction="在锚点后创建待办清单",
        expected="锚点后出现两项待办清单",
        product="Docs",
        stage="docs_realistic_composition",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.TYPE_TEXT, text="DOCS-FEATURE-MATERIAL-ROOT-7A2D\n整份素材")),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_accidental_full_material_paste" in quality["blocking_warnings"]


def test_process_quality_allows_full_material_paste_for_material_import_case():
    case = TestCase(
        id="DOCS-FEAT-PREP-001",
        name="导入 Docs 深水区功能素材",
        instruction="把整份素材导入文档正文",
        expected="正文出现素材根标识",
        product="Docs",
        stage="docs_feature_prep",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.TYPE_TEXT, text="DOCS-FEATURE-MATERIAL-ROOT-7A2D\n整份素材")),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_accidental_full_material_paste" not in quality["blocking_warnings"]


def test_process_quality_blocks_bounded_material_marker_leak_and_raw_markdown():
    case = TestCase(
        id="DOCS-FEAT-COMP-014",
        name="从本地 Markdown 局部复制粘贴议程",
        instruction="从本地 Markdown 素材中只复制 START 和 END 之间的议程片段，粘贴到锚点后",
        expected="指定锚点后出现议程片段",
        product="Docs",
        stage="docs_realistic_composition",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.TYPE_TEXT,
                    text="DOCS-FEATURE-LOCAL-MD-SNIPPET-START-58AF\n### 标题\n- 同步目标\nDOCS-FEATURE-LOCAL-MD-SNIPPET-END-58AF",
                ),
            ),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_material_boundary_marker_leak" in quality["blocking_warnings"]
    assert "docs_raw_markdown_residue" in quality["blocking_warnings"]


def test_process_quality_blocks_literal_markdown_table_for_rendered_table_task():
    case = TestCase(
        id="DOCS-FEAT-COMP-015",
        name="从本地 Markdown 局部复制粘贴表格",
        instruction="从本地 Markdown 素材中复制小表格，粘贴到锚点后",
        expected="指定锚点后出现素材小表格或表格化内容",
        product="Docs",
        stage="docs_realistic_composition",
        verification={"assertion": "锚点后可见包含阶段、动作、验收的表格网格或渲染表格结构"},
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.TYPE_TEXT,
                    text="| 阶段 | 动作 | 验收 |\n| --- | --- | --- |\n| 准备 | 局部粘贴 | 可见 |",
                    target="body insertion point",
                ),
            ),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_literal_markdown_table_without_rendered_table_path" in quality["blocking_warnings"]


def test_process_quality_blocks_literal_slash_command_text_for_docs_structure():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="在锚点后插入三列表格",
        expected="锚点后出现表格",
        product="Docs",
        stage="docs_realistic_composition",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[StepResult(index=1, action=Action(kind=ActionKind.TYPE_TEXT, text="/表格"))],
    )

    quality = evaluate_process_quality(result)

    assert "docs_stray_slash_command_text_input" in quality["blocking_warnings"]


def test_process_quality_blocks_dirty_table_selection_without_real_repair():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="在锚点后插入表格；如果看到数据堆在同一批单元格里，必须修复。",
        expected="表头和数据在不同表格行，中间有横向行边界",
        product="Docs",
        stage="docs_realistic_composition",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.DOUBLE_CLICK, target="素材复核 text in first table cell")),
            StepResult(index=2, action=Action(kind=ActionKind.HOTKEY, key="command f")),
            StepResult(index=3, action=Action(kind=ActionKind.HOTKEY, key="esc")),
            StepResult(index=4, action=Action(kind=ActionKind.FINISHED)),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_table_repair_no_modification" in quality["blocking_warnings"]


def test_process_quality_allows_dirty_table_repair_with_cut_and_paste():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="在锚点后插入表格；如果看到数据堆在同一批单元格里，必须修复。",
        expected="表头和数据在不同表格行，中间有横向行边界",
        product="Docs",
        stage="docs_realistic_composition",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.DOUBLE_CLICK, target="素材复核 text in first table cell")),
            StepResult(index=2, action=Action(kind=ActionKind.HOTKEY, key="command x")),
            StepResult(index=3, action=Action(kind=ActionKind.CLICK, target="empty data row cell")),
            StepResult(index=4, action=Action(kind=ActionKind.HOTKEY, key="command v")),
            StepResult(index=5, action=Action(kind=ActionKind.FINISHED)),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_table_repair_no_modification" not in quality["blocking_warnings"]


def test_process_quality_blocks_dirty_table_drag_selection_without_real_repair():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        name="在锚点后插入三列表格",
        instruction="在锚点后插入表格；如果看到数据堆在同一批单元格里，必须修复。",
        expected="表头和数据在不同表格行，中间有横向行边界",
        product="Docs",
        stage="docs_realistic_composition",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(index=1, action=Action(kind=ActionKind.DRAG, target="stacked 素材复核 text")),
            StepResult(index=2, action=Action(kind=ActionKind.DRAG, target="stacked 素材复核 text")),
            StepResult(index=3, action=Action(kind=ActionKind.FINISHED)),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_table_repair_no_modification" in quality["blocking_warnings"]


def test_process_quality_warns_when_partial_format_final_still_mentions_selection():
    case = TestCase(
        id="DOCS-FEAT-COMP-008",
        name="只格式化句中局部短语",
        instruction="只把短语设置为高亮或加粗",
        expected="只有指定短语呈现高亮或加粗样式",
        product="Docs",
        stage="docs_realistic_composition",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        steps=[
            StepResult(
                index=1,
                action=Action(kind=ActionKind.FINISHED),
                raw_model='CompletionCheck: {"status":"satisfied","reason":"the target phrase is selected and bold"}',
            ),
        ],
    )

    quality = evaluate_process_quality(result)

    assert "docs_final_selection_should_be_cleared" in quality["warnings"]
