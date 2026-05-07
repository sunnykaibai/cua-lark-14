from __future__ import annotations

from typing import Any

from cua_lark.domain.models import ActionKind, CaseResult


def evaluate_process_quality(result: CaseResult) -> dict[str, Any]:
    actions = _flatten_actions([step.action for step in result.steps if step.action])
    warnings: list[str] = []
    type_text_actions = [action for action in actions if action.kind == ActionKind.TYPE_TEXT and action.text]
    type_texts = [action.text for action in type_text_actions]
    enter_sends = [action for action in actions if action.kind == ActionKind.HOTKEY and action.key.lower() == "enter"]
    grounding_checks = [action.grounding_check for action in actions if action.grounding_check]
    corrected_checks = [item for item in grounding_checks if item.get("changed_point")]
    skipped_checks = [item for item in grounding_checks if item.get("triggered") is False]
    failed_steps = [step for step in result.steps if not step.passed and step.message]

    plain_at_inputs = [text for text in type_texts if _looks_like_plain_mention_text(text)]
    clicked_mention_button = any(
        action.kind == ActionKind.CLICK and _contains_any(action.target, ["@", "mention", "提及"])
        for action in actions
    )
    selected_mention_option = any(action.kind == ActionKind.CLICK and _is_mention_option_target(action.target) for action in actions)

    if len(enter_sends) > 1 and not _is_docs_structure_case(result):
        warnings.append(f"multiple_enter_sends:{len(enter_sends)}")
    if _is_mention_case(result) and plain_at_inputs:
        warnings.append(f"plain_at_text_inputs:{len(plain_at_inputs)}")
    if _is_mention_case(result) and not clicked_mention_button:
        warnings.append("mention_button_not_observed")
    if _is_mention_case(result) and not selected_mention_option:
        warnings.append("mention_option_not_observed")
    if corrected_checks:
        warnings.append(f"grounding_corrected:{len(corrected_checks)}")
    if failed_steps:
        warnings.append(f"failed_steps_present:{len(failed_steps)}")
    blocking_warnings: list[str] = []
    if _is_reply_case(result) and not _has_reply_operation_evidence(actions):
        blocking_warnings.append("reply_without_reference_operation")
    if _is_cloud_share_case(result) and _has_clipboard_paste(actions):
        blocking_warnings.append("cloud_share_clipboard_paste")
    if _is_docs_body_edit_case(result) and _has_duplicate_body_type_text(type_text_actions):
        blocking_warnings.append("docs_duplicate_exact_body_text_input")
    if _is_docs_body_edit_case(result) and not _is_docs_provision_case(result) and _has_body_click_near_title(actions):
        blocking_warnings.append("docs_body_click_may_target_title_area")
    if _is_docs_task(result) and _has_stray_slash_command_text(type_text_actions):
        blocking_warnings.append("docs_stray_slash_command_text_input")
    if _is_docs_task(result) and _has_accidental_full_material_paste(result, type_text_actions):
        blocking_warnings.append("docs_accidental_full_material_paste")
    if _is_docs_bounded_material_task(result) and _has_material_boundary_marker_leak(type_text_actions):
        blocking_warnings.append("docs_material_boundary_marker_leak")
    if _is_docs_rendered_table_task(result) and _has_literal_markdown_table_without_table_path(actions, type_text_actions):
        blocking_warnings.append("docs_literal_markdown_table_without_rendered_table_path")
    if _is_docs_local_markdown_task(result) and _has_raw_markdown_residue(type_text_actions):
        blocking_warnings.append("docs_raw_markdown_residue")
    if _is_docs_table_repair_case(result) and _finished_without_table_modification(actions):
        blocking_warnings.append("docs_table_repair_no_modification")
    if _is_docs_partial_format_case(result) and _final_response_mentions_active_selection(result):
        warnings.append("docs_final_selection_should_be_cleared")
    warnings.extend(blocking_warnings)

    return {
        "status": "clean" if not warnings else "warning",
        "warnings": warnings,
        "blocking_warnings": blocking_warnings,
        "action_count": len(actions),
        "type_text_count": len(type_texts),
        "enter_send_count": len(enter_sends),
        "plain_at_text_input_count": len(plain_at_inputs),
        "mention_button_observed": clicked_mention_button,
        "mention_option_observed": selected_mention_option,
        "grounding_check_count": len(grounding_checks),
        "grounding_check_corrected_count": len(corrected_checks),
        "grounding_check_skipped_count": len(skipped_checks),
    }


def _is_mention_case(result: CaseResult) -> bool:
    text = " ".join(
        [
            result.case.instruction,
            result.case.name,
            result.case.expected,
            str(result.case.verification.get("assertion") or ""),
        ]
    )
    return "@" in text or "提及" in text or "mention" in text.lower()


def _flatten_actions(actions: list[Any]) -> list[Any]:
    flattened: list[Any] = []
    for action in actions:
        if not action:
            continue
        if getattr(action, "kind", None) == ActionKind.BATCH:
            flattened.extend(_flatten_actions(list(getattr(action, "sub_actions", []) or [])))
            continue
        flattened.append(action)
    return flattened


def _is_reply_case(result: CaseResult) -> bool:
    text = " ".join(
        [
            result.case.instruction,
            result.case.name,
            result.case.expected,
            str(result.case.verification.get("assertion") or ""),
        ]
    ).lower()
    return "回复" in text or "引用" in text or "reply" in text or "reference" in text


def _has_reply_operation_evidence(actions: list[Any]) -> bool:
    for action in actions:
        text = " ".join([action.target, action.thought, str(action.grounding.get("evidence") or "")]).lower()
        if action.kind == ActionKind.RIGHT_CLICK and _contains_any(text, ["message", "消息", "bubble", "气泡", "chat"]):
            return True
        if _contains_any(text, ["reply", "回复", "引用", "quote", "reference"]):
            return True
    return False


def _is_cloud_share_case(result: CaseResult) -> bool:
    text = " ".join(
        [
            result.case.instruction,
            result.case.name,
            result.case.stage,
        ]
    ).lower()
    return ("云文档" in text or "document" in text) and ("分享" in text or "发送" in text or "share" in text)


def _is_docs_body_edit_case(result: CaseResult) -> bool:
    text = " ".join(
        [
            result.case.instruction,
            result.case.name,
            result.case.stage,
            result.case.product,
        ]
    ).lower()
    return "docs" in text and any(term in text for term in ["正文", "body", "编辑", "edit", "追加", "append"])


def _is_docs_task(result: CaseResult) -> bool:
    text = " ".join([result.case.product, result.case.stage, result.case.instruction, result.case.name]).lower()
    return "docs" in text or "云文档" in text or "飞书文档" in text


def _is_docs_provision_or_material_import_case(result: CaseResult) -> bool:
    text = " ".join(
        [
            result.case.instruction,
            result.case.name,
            result.case.stage,
            result.case.expected,
        ]
    ).lower()
    return any(
        term in text
        for term in [
            "provision",
            "prep",
            "导入",
            "创建 layer",
            "创建 docs",
            "整份素材",
            "全文素材",
            "material-root",
            "material root",
        ]
    )


def _is_docs_provision_case(result: CaseResult) -> bool:
    """Detect document creation/provisioning cases where body starts near title."""
    text = " ".join([result.case.instruction, result.case.name]).lower()
    return _is_docs_task(result) and any(
        term in text for term in ["新建一个文档", "新建文档", "创建文档", "create document", "create a document", "provision"]
    )


def _is_docs_bounded_material_task(result: CaseResult) -> bool:
    text = " ".join([result.case.instruction, result.case.name, result.case.expected]).lower()
    return _is_docs_task(result) and any(term in text for term in ["片段", "snippet", "start", "end", "之间", "局部"])


def _is_docs_local_markdown_task(result: CaseResult) -> bool:
    text = " ".join([result.case.instruction, result.case.name, result.case.expected]).lower()
    return _is_docs_task(result) and any(term in text for term in ["本地 markdown", "local markdown", "markdown 素材"])


def _is_docs_rendered_table_task(result: CaseResult) -> bool:
    text = " ".join([result.case.instruction, result.case.name, result.case.expected, str(result.case.verification.get("assertion") or "")]).lower()
    if not _is_docs_task(result):
        return False
    if not any(term in text for term in ["表格", "table"]):
        return False
    return any(term in text for term in ["网格", "渲染", "rendered", "真实", "结构", "table grid", "表格结构"])


def _is_docs_table_repair_case(result: CaseResult) -> bool:
    text = " ".join(
        [
            result.case.instruction,
            result.case.name,
            result.case.expected,
            str(result.case.verification.get("assertion") or ""),
        ]
    ).lower()
    if not _is_docs_task(result) or not any(term in text for term in ["表格", "table"]):
        return False
    return any(term in text for term in ["修复", "堆", "stack", "row boundary", "横向行边界", "不同表格行"])


def _finished_without_table_modification(actions: list[Any]) -> bool:
    if not any(action.kind == ActionKind.FINISHED for action in actions):
        return False
    return not any(_is_table_modification_action(action) for action in actions)


def _is_table_modification_action(action: Any) -> bool:
    if action.kind == ActionKind.TYPE_TEXT and (action.text or "").strip():
        return True
    if action.kind != ActionKind.HOTKEY:
        return False
    key = (action.key or "").replace("+", " ").strip().lower()
    return key in {
        "command x",
        "cmd x",
        "meta x",
        "command v",
        "cmd v",
        "meta v",
        "backspace",
        "delete",
    }


def _is_docs_partial_format_case(result: CaseResult) -> bool:
    text = " ".join([result.case.instruction, result.case.name, result.case.expected]).lower()
    return _is_docs_task(result) and any(term in text for term in ["局部", "短语", "partial", "format", "高亮", "加粗"])


def _is_docs_structure_case(result: CaseResult) -> bool:
    text = " ".join(
        [
            result.case.instruction,
            result.case.name,
            result.case.stage,
            result.case.product,
        ]
    ).lower()
    return "docs" in text and any(
        term in text for term in ["列表", "项目符号", "编号", "一级标题", "heading", "list", "bullet", "numbered"]
    )


def _has_stray_slash_command_text(actions: list[Any]) -> bool:
    slash_texts = {"/", "//", "/表格", "/table", "/分割线", "/divider"}
    for action in actions:
        if action.kind != ActionKind.TYPE_TEXT:
            continue
        normalized = (action.text or "").strip().lower()
        if normalized in slash_texts:
            return True
        if normalized.startswith("/") and any(term in normalized for term in ["表格", "table", "分割线", "divider"]):
            return True
    return False


def _has_accidental_full_material_paste(result: CaseResult, actions: list[Any]) -> bool:
    if _is_docs_provision_or_material_import_case(result):
        return False
    return any("DOCS-FEATURE-MATERIAL-ROOT-" in (action.text or "") for action in actions)


def _has_material_boundary_marker_leak(actions: list[Any]) -> bool:
    boundary_markers = [
        "SNIPPET-START",
        "SNIPPET-END",
        "LOCAL-MD-SNIPPET-START",
        "LOCAL-MD-SNIPPET-END",
        "LOCAL-TABLE-START",
        "LOCAL-TABLE-END",
    ]
    return any(_contains_any(action.text or "", boundary_markers) for action in actions)


def _has_literal_markdown_table_without_table_path(actions: list[Any], type_text_actions: list[Any]) -> bool:
    if not any(_looks_like_markdown_table(action.text or "") for action in type_text_actions):
        return False
    semantic = " ".join(
        " ".join([action.target, action.thought, str(action.grounding.get("evidence") or ""), action.key, action.text])
        for action in actions
    ).lower()
    return not _contains_any(semantic, ["slash menu", "slash-command menu", "table option", "表格 option", "rendered table", "table grid"])


def _has_raw_markdown_residue(actions: list[Any]) -> bool:
    for action in actions:
        text = action.text or ""
        if "### " in text:
            return True
        lines = [line.strip() for line in text.splitlines()]
        if any(line.startswith("- ") for line in lines):
            return True
    return False


def _final_response_mentions_active_selection(result: CaseResult) -> bool:
    if not result.steps:
        return False
    raw = (result.steps[-1].raw_model or "").lower()
    return _contains_any(raw, ["selected", "selection", "选中", "选区", "highlighted selection"])


def _looks_like_markdown_table(value: str) -> bool:
    lines = [line.strip() for line in (value or "").splitlines() if line.strip()]
    pipe_lines = [line for line in lines if line.startswith("|") and line.endswith("|") and line.count("|") >= 3]
    if len(pipe_lines) < 2:
        return False
    return any(set(line.replace("|", "").strip()) <= {"-", ":", " "} for line in pipe_lines)


def _has_duplicate_body_type_text(actions: list[Any]) -> bool:
    seen: set[str] = set()
    for action in actions:
        semantic = " ".join([action.target, action.thought, str(action.grounding.get("evidence") or "")]).lower()
        if _contains_any(
            semantic,
            [
                "search",
                "搜索",
                "query",
                "title",
                "标题",
                "name field",
                "document name",
            ],
        ):
            continue
        value = action.text
        normalized = (value or "").strip()
        if not normalized:
            continue
        if normalized in seen:
            return True
        seen.add(normalized)
    return False


def _has_body_click_near_title(actions: list[Any]) -> bool:
    for action in actions:
        if action.kind != ActionKind.CLICK:
            continue
        semantic = " ".join([action.target, action.thought, str(action.grounding.get("evidence") or "")]).lower()
        if not _contains_any(semantic, ["body", "正文"]):
            continue
        if _contains_any(
            semantic,
            [
                "paragraph",
                "段落",
                "anchor",
                "锚点",
                "last line",
                "last document",
                "body end",
                "document body end",
                "end of",
                "末尾",
                "正文末尾",
            ],
        ):
            continue
        if _contains_any(semantic, ["placeholder", "占位", "insertion", "插入", "empty body", "空白正文", "new document", "新建文档", "新文档", "blank document", "title field", "标题下方"]):
            continue
        box = action.grounding.get("box_0_1000")
        point = action.grounding.get("point_0_1000")
        try:
            y2 = int(box[3]) if isinstance(box, list) and len(box) == 4 else None
            y = int(point[1]) if isinstance(point, list) and len(point) == 2 else None
        except (TypeError, ValueError):
            continue
        if y2 is not None and y2 < 360:
            return True
        if y2 is None and y is not None and y < 360:
            return True
    return False


def _has_clipboard_paste(actions: list[Any]) -> bool:
    return any(
        action.kind == ActionKind.HOTKEY
        and action.key.replace("+", " ").strip().lower() in {"command v", "cmd v", "meta v"}
        for action in actions
    )


def _contains_any(value: str, needles: list[str]) -> bool:
    lowered = (value or "").lower()
    return any(needle.lower() in lowered for needle in needles)


def _is_mention_option_target(value: str) -> bool:
    lowered = (value or "").lower()
    return any(term in lowered for term in ["mention pop-up", "mention popup", "@ mention", "提及弹出", "选项", "option"])


def _looks_like_plain_mention_text(value: str) -> bool:
    text = (value or "").strip()
    if not text or text == "@":
        return False
    return text.startswith("@")
