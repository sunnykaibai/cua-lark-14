from __future__ import annotations

from cua_lark.domain.models import Action, ActionKind, GoalContract, StepResult, TestCase


def build_step_prompt(
    case: TestCase,
    history: list[StepResult],
    rules_prompt: str = "",
    goal_contract: GoalContract | None = None,
    case_started_at: str = "",
    current_time: str = "",
    include_contract: bool = False,
) -> str:
    lines = [
        "# Task",
        f"instruction: {case.instruction}",
        f"allowed_actions: {_allowed_actions_line(case)}",
    ]
    if case.input_materials:
        lines.extend(_input_material_lines(case))
    lines.extend(
        [
            "",
            "# Time",
            f"case_started_at: {case_started_at or 'unknown'}",
            f"current_time: {current_time or 'unknown'}",
        ]
    )
    if goal_contract and _goal_contract_has_content(goal_contract):
        lines.extend(
            [
                "",
                "# Goal Contract",
                f"goal: {goal_contract.goal}",
                "completion_evidence:",
            ]
        )
        lines.extend([f"- {item}" for item in goal_contract.completion_evidence] or ["- none"])
        lines.append("non_completion_evidence:")
        lines.extend([f"- {item}" for item in goal_contract.non_completion_evidence] or ["- none"])
        lines.append("must_not:")
        lines.extend([f"- {item}" for item in goal_contract.must_not] or ["- none"])
    lines.extend(
        [
            "",
            "# History",
        ]
    )
    if not history:
        lines.append("- none")
    else:
        for step in history[-6:]:
            lines.append(_history_fact(step))
        latest_success = _latest_successful_step(history)
        if latest_success is not None:
            lines.extend(
                [
                    "",
                    "# Latest Successful Action",
                    _latest_success_fact(latest_success),
                ]
            )
        latest_side_effect = _latest_side_effect_step(history)
        if latest_side_effect is not None and latest_side_effect is not latest_success:
            lines.extend(
                [
                    "",
                    "# Latest Side-Effect Action",
                    _latest_side_effect_fact(latest_side_effect),
                ]
            )
    if rules_prompt.strip():
        lines.extend(
            [
                "",
                "# Operation Rules",
                rules_prompt.strip(),
            ]
        )
    lines.extend(_recovery_protocols(case, history))
    lines.extend(_product_protocols(case))
    if include_contract:
        lines.extend(
            [
                "",
                "# Extra Output Contract",
                "- This block is only for legacy/debug runs. The canonical action schema lives in the system prompt.",
                "- Use only allowed_actions; case actions override scenario actions.",
                "- Never include a batch sub-action whose operation type is absent from allowed_actions.",
                "- Use the current screenshot, successful history, and loaded Operation Rules; keep successful history unless contradicted by the screenshot.",
                "",
                "# Batch",
                "- You must use Action: batch() if and only if all sub-actions are decidable from the current screenshot plus successful history.",
                "- Include every visible/unchanged sub-action target whose execution will not invalidate later targets; do not split batchable operations into separate steps.",
                "- Stop exactly before acting inside UI that appears only after a new popup/menu/picker/panel opens.",
                "- A UI-opening action may be the final sub-action.",
                "- For batch output, add one compact JSON Actions line. Click/scroll sub-actions need target, point, bbox, confidence, evidence.",
                "",
                "# Output",
                "- Include exactly one State line before Action: State: ui='<visible>', carried='<kept facts or none>', next='<missing step>'.",
                "- Single-action Grounding must use tagged coordinates: bbox='<box>x1 y1 x2 y2</box>', point='<point>x y</point>'; never bare numbers.",
                "- Always include Action. If unsure, Action: wait().",
                "- Optional Elements line: at most 3 visible elements, action target plus nearby confusable controls.",
                "- Do not mention hidden verifier assertions. Do not invent coordinates for invisible targets.",
            ]
        )
    return "\n".join(lines)


def _history_fact(step: StepResult) -> str:
    if not step.action:
        return f"- S{step.index}: failed parse_error"
    action = step.action
    status = "ok" if step.passed else "failed"
    message = step.message or status
    fields = [
        f"- S{step.index}: {status}",
        f"action={action.kind.value}",
    ]
    if action.target:
        fields.append(f"target={_quote_fact(action.target)}")
    if action.text:
        fields.append(f"content={_quote_fact(action.text)}")
    if action.key:
        fields.append(f"key={_quote_fact(action.key)}")
    sub_actions = _sub_actions_history(action)
    if sub_actions:
        fields.append(f"sub_actions={_quote_fact(sub_actions)}")
    if action.expected:
        fields.append(f"expected_result={_quote_fact(action.expected)}")
    fields.append(f"result={_quote_fact(message)}")
    return "; ".join(fields)


def _latest_successful_step(history: list[StepResult]) -> StepResult | None:
    for step in reversed(history):
        if step.passed:
            return step
    return None


def _latest_side_effect_step(history: list[StepResult]) -> StepResult | None:
    for step in reversed(history):
        if step.passed and step.action and _is_side_effect_action(step.action):
            return step
    return None


def _latest_success_fact(step: StepResult) -> str:
    action = step.action
    if not action:
        return f"- S{step.index}: none"
    fields = [f"- S{step.index}: action={action.kind.value}"]
    if action.target:
        fields.append(f"target={_quote_fact(action.target)}")
    if action.text:
        fields.append(f"content={_quote_fact(action.text)}")
    if action.key:
        fields.append(f"key={_quote_fact(action.key)}")
    sub_actions = _sub_actions_history(action)
    if sub_actions:
        fields.append(f"sub_actions={_quote_fact(sub_actions)}")
    if action.expected:
        fields.append(f"expected_result={_quote_fact(action.expected)}")
    fields.append(
        "use this expected_result to judge whether the current screenshot already satisfies the task before any new action"
    )
    return "; ".join(fields)


def _latest_side_effect_fact(step: StepResult) -> str:
    action = step.action
    if not action:
        return f"- S{step.index}: none"
    fields = [f"- S{step.index}: action={action.kind.value}"]
    if action.target:
        fields.append(f"target={_quote_fact(action.target)}")
    sub_actions = _sub_actions_history(action)
    if sub_actions:
        fields.append(f"sub_actions={_quote_fact(sub_actions)}")
    if action.expected:
        fields.append(f"expected_result={_quote_fact(action.expected)}")
    fields.append(
        "do not repeat this side-effect action unless the current screenshot clearly shows it failed"
    )
    return "; ".join(fields)


def _sub_actions_history(action: object) -> str:
    if not action or not getattr(action, "sub_actions", None):
        return ""
    parts = []
    for sub_action in action.sub_actions:
        detail = sub_action.kind.value
        if sub_action.text:
            detail += f"({sub_action.text})"
        elif sub_action.key:
            detail += f"({sub_action.key})"
        elif sub_action.target:
            detail += f"({sub_action.target})"
        parts.append(detail)
    return " -> ".join(parts)


def _is_side_effect_action(action: Action) -> bool:
    if action.kind == ActionKind.TYPE_TEXT:
        return True
    if action.kind == ActionKind.HOTKEY and action.key.strip().lower() == "enter":
        return True
    if action.kind == ActionKind.BATCH:
        return any(_is_side_effect_action(sub_action) for sub_action in action.sub_actions)
    target = (action.target or "").lower()
    expected = (action.expected or "").lower()
    text = f"{target} {expected}"
    return any(term in text for term in ["send", "sent", "发送", "submit", "create", "share", "upload"])


def _quote_fact(value: object) -> str:
    text = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def build_verify_prompt(case: TestCase) -> str:
    assertion = case.verification.get("assertion") or case.expected
    return "\n".join(
        [
            "You are verifying the final screenshot of a GUI test.",
            "Answer the checklist explicitly, then give Verdict.",
            "ObjectType: what object type did the user request, such as text message, emoji message, mention token, reply, reaction, file, image, card, or document share?",
            "NewestObject: what is the newest real live UI object relevant to that request in the current conversation?",
            "MatchesType: yes/no, does NewestObject have the requested object type?",
            "MatchesContent: yes/no, does NewestObject contain the requested content/state?",
            "ExtraUnrequestedObjects: yes/no, does NewestObject include any extra object not requested by the user, such as an image, screenshot, file, card, link preview, extra mention, or wrong attachment?",
            "UnfinishedComposer: yes/no, is there an unfinished composer draft, attachment preview, popup state, or wrong object left after the task?",
            "Verdict: PASS only if MatchesType=yes, MatchesContent=yes, ExtraUnrequestedObjects=no, and UnfinishedComposer=no; otherwise FAIL.",
            "Judge only real live chat/UI objects, not text or controls depicted inside screenshots, images, cards, attachment previews, or conversation-list previews.",
            "If only older similar objects satisfy the request while the newest task-relevant live object does not, return FAIL.",
            "Return exactly these fields: ObjectType, NewestObject, MatchesType, MatchesContent, ExtraUnrequestedObjects, UnfinishedComposer, Verdict, Reason.",
            f"User instruction: {case.instruction}",
            f"Expected result: {case.expected}",
            f"Assertion: {assertion}",
        ]
    )


def _allowed_actions_line(case: TestCase) -> str:
    if not case.allowed_actions:
        return "Use only the actions listed in the scenario system prompt."
    return ", ".join(case.allowed_actions)


def _goal_contract_has_content(contract: GoalContract) -> bool:
    return bool(
        contract.goal
        or contract.completion_evidence
        or contract.non_completion_evidence
        or contract.must_not
    )


def _input_material_lines(case: TestCase) -> list[str]:
    if not case.input_materials:
        return []
    lines = ["", "# Input Materials"]
    for item in case.input_materials:
        if isinstance(item, dict):
            lines.append(f"- {item.get('label', 'material')}: {item.get('content', '')[:500]}")
    return lines


def _recovery_protocols(case: TestCase, history: list[StepResult]) -> list[str]:
    result: list[str] = []
    docs = (case.product or "").lower() == "docs"
    if docs:
        result.extend(_focus_stability_protocol(history))
        result.extend(_input_no_change_recovery_protocol(history))
        result.extend(_docs_insertion_focus_protocol(case, history))
        result.extend(_docs_structure_insertion_click_protocol(case, history))
        result.extend(_docs_move_recovery_protocol(case, history))
        result.extend(_docs_popup_close_recovery_protocol(case, history))
        result.extend(_docs_entry_repeat_protocol(case, history))
        result.extend(_docs_repeated_find_protocol(case, history))
        result.extend(_docs_structure_after_find_protocol(case, history))
        result.extend(_docs_slash_command_repeat_protocol(case, history))
    return result


def _product_protocols(case: TestCase) -> list[str]:
    lines: list[str] = []
    lines.extend(_mentions_protocol(case))
    lines.extend(_message_operation_protocol(case))
    lines.extend(_attachment_share_protocol(case))
    lines.extend(_rich_text_protocol(case))
    lines.extend(_batch_protocol(case))
    lines.extend(_general_product_navigation_protocol(case))
    lines.extend(_composer_protocol(case))
    docs = (case.product or "").lower() == "docs"
    if docs:
        lines.extend(_docs_protocol(case))
    return lines


def _focus_stability_protocol(history: list[StepResult]) -> list[str]:
    if not history:
        return []
    last = history[-1]
    if not isinstance(last.visual_change, dict) or last.visual_change.get("status") != "focus-likely":
        return []
    return [
        "Input focus stability protocol:",
        "- The previous click likely focused an input/composer/search field; caret visibility may blink and is not a stable screenshot signal.",
        "- Do not repeat the same input click only because the caret is not visible. If the task needs text input and no blocking popup appeared, proceed with type_text.",
        "",
    ]


def _input_no_change_recovery_protocol(history: list[StepResult]) -> list[str]:
    if not history:
        return []
    recent_type_steps = [
        step
        for step in history[-3:]
        if step.action
        and step.action.kind == ActionKind.TYPE_TEXT
        and isinstance(step.visual_change, dict)
        and step.visual_change.get("status") == "no-visible-change"
    ]
    if len(recent_type_steps) < 2:
        return []
    last_text = recent_type_steps[-1].action.text if recent_type_steps[-1].action else ""
    prev_text = recent_type_steps[-2].action.text if recent_type_steps[-2].action else ""
    if last_text != prev_text:
        return []
    return [
        "Input no-change recovery protocol:",
        "- The same text was typed more than once, but the screenshot did not visibly change.",
        "- Do not type that same text again as the next action.",
        "- If the old query/text is still visible or selected in a search/input field, first refocus the visible field or clear it with backspace/visible clear control, then type once.",
        "- If the intended query is already visible and a matching result is shown, open the visible result or press Enter instead of repeating type_text.",
        "",
    ]


def _docs_insertion_focus_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if not history:
        return []
    last = history[-1]
    if not last.action or last.action.kind.value != "click":
        return []
    visual_status = last.visual_change.get("status", "unknown") if isinstance(last.visual_change, dict) else last.visual_change
    target_text = " ".join([last.action.target, last.action.thought]).lower()
    if visual_status not in {"no-visible-change", "focus-likely", "small-change"}:
        return []
    if not any(term in target_text for term in ["paragraph", "段落", "正文", "body", "end of", "末尾", "cursor", "光标"]):
        return []
    return [
        "Docs insertion focus protocol:",
        "- The previous click targeted a document body paragraph or insertion point. In Docs, caret/focus changes can be visually subtle.",
        "- If no blocking popup appeared and the next task is to add or edit text, do not keep clicking the same paragraph endpoint.",
        "- Proceed with the requested type_text content, or use shift enter/enter first only if a new paragraph is needed before typing.",
        "",
    ]


def _docs_structure_insertion_click_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if not history:
        return []
    text = " ".join([case.id, case.name, case.instruction, case.stage]).lower()
    if "表格" not in text and "分割线" not in text and "divider" not in text:
        return []
    last = history[-1]
    if not last.action or last.action.kind != ActionKind.CLICK:
        return []
    target_text = " ".join([last.action.target, last.action.thought, last.action.raw_text]).lower()
    if not _is_docs_structure_insertion_point_text(target_text):
        return []
    return [
        "Docs structure insertion-point protocol:",
        "- The previous click targeted the trailing end of an anchor line or a body insertion point for a table/divider/structure task.",
        "- Caret placement in Docs may be visually subtle; do not repeat that same insertion-point click as the next action.",
        "- If the anchor sentence has trailing punctuation such as '。' or '.', keep the caret after that punctuation, then create a true empty body block with hotkey enter or shift enter before opening slash/table/divider controls.",
        "",
    ]


def _docs_move_recovery_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if not history:
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not _docs_edit_task(text) or "move" not in text and "移动" not in text:
        return []
    observed_zero = any(
        _contains_any(
            " ".join(
                [
                    step.action.target if step.action else "",
                    step.action.thought if step.action else "",
                    step.message or "",
                    step.raw_model or "",
                ]
            ).lower(),
            ["0 matches", "0/0", "0 / 0", "no matches"],
        )
        for step in history
    )
    if not observed_zero:
        return []
    return [
        "Docs move dirty-data recovery protocol:",
        "- A prior step already observed zero matches for the source paragraph. Do not search, scroll, or infer that the source is above/below the current viewport.",
        "- If the target paragraph is visible, do not leave it to hunt for the missing source. Insert the source immediately before that target.",
        "",
    ]


def _docs_popup_close_recovery_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if not history:
        return []
    recent_close_clicks = [
        step
        for step in history[-3:]
        if step.action
        and step.action.kind == ActionKind.CLICK
        and _contains_any(
            " ".join([step.action.target, step.action.thought, step.action.raw_text]).lower(),
            ["close", "关闭", "x button", "搜索弹窗", "search popup"],
        )
        and isinstance(step.visual_change, dict)
        and step.visual_change.get("status") in {"no-visible-change", "small-change"}
    ]
    if len(recent_close_clicks) < 1:
        return []
    return [
        "Docs popup close recovery protocol:",
        "- The previous click tried to close a Docs popup or search popup but produced little or no visible change.",
        "- Do not click the same close/X target again as the next action.",
        "- Prefer hotkey esc once to dismiss the popup. If Esc was already tried and the popup-looking area still remains, treat it as embedded page/document content and continue through visible Docs navigation or create controls.",
        "",
    ]


def _docs_entry_repeat_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if not history:
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not _docs_entry_open_task(text):
        return []
    recent_clicks = [
        step
        for step in history[-4:]
        if step.action
        and step.action.kind in {ActionKind.CLICK, ActionKind.DOUBLE_CLICK}
        and _contains_any(
            " ".join([step.action.target, step.action.thought, step.action.raw_text]),
            ["search result", "document result", "document row", "document title", "文档", "搜索结果"],
        )
    ]
    if len(recent_clicks) < 2:
        return []
    targets = [" ".join([step.action.target, step.action.thought]).lower() for step in recent_clicks]
    repeated = any(
        targets[i] and targets[i + 1] and (targets[i] in targets[i + 1] or targets[i + 1] in targets[i])
        for i in range(len(targets) - 1)
    )
    if not repeated:
        return []
    return [
        "Docs entry repeat-stop protocol:",
        "- You have already clicked the same visible document/search result more than once in this entry/open task.",
        "- First inspect the current screenshot: if the requested document title is now visible as the opened page title, return finished immediately.",
        "- If the same search popup/result is still visible, do not click that same result again. Use hotkey esc once to close a blocking search popup, then continue from the underlying Docs entry surface or a different visible open affordance.",
        "",
    ]


def _docs_repeated_find_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if not history:
        return []
    find_attempts = [
        step
        for step in history[-6:]
        if step.action
        and _contains_any(
            " ".join([step.action.target, step.action.thought, step.action.raw_text]).lower(),
            ["find", "查找", "command f", "文档内搜索", "in-document search"],
        )
    ]
    if len(find_attempts) < 3:
        return []
    return [
        "Docs repeated-find stop protocol:",
        "- Recent successful steps have repeatedly opened or typed into document find/search. Do not issue command f, type the same anchor, or reopen the find panel again as the next action.",
        "- First inspect the current screenshot. If the requested anchor/phrase is visible in the page, operate directly on that visible text or its adjacent insertion point.",
        "",
    ]


def _docs_slash_command_repeat_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if not history:
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if "表格" not in text and "分割线" not in text and "divider" not in text:
        return []
    slash_attempts = [
        step
        for step in history[-8:]
        if step.action
        and (
            step.action.text.strip().lower() in {"/", "/表格", "/table", "/分割线", "/divider"}
            or _contains_any(
                " ".join([step.action.text, step.action.thought, step.action.target, step.action.raw_text]).lower(),
                ["slash", "表格", "table", "分割线", "divider"],
            )
        )
    ]
    if len(slash_attempts) < 2:
        return []
    return [
        "Docs slash-command repeat-stop protocol:",
        "- Recent steps already tried slash-command text for this structure task, but no visible slash menu or rendered structure appeared.",
        "- Do not type '/', '/表格', '/table', '/分割线', or similar slash text again as the next action.",
        "- If literal slash-command text is visible in the body, clear it once; then use a visible Docs toolbar, block handle, insert '+', table/divider menu item, or another non-slash visible control.",
        "",
    ]


def _docs_structure_after_find_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if not history:
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if "表格" not in text and "分割线" not in text and "divider" not in text:
        return []
    saw_find = any(
        step.action
        and (
            (step.action.kind == ActionKind.HOTKEY and (step.action.key or "").lower() == "command f")
            or _contains_any(" ".join([step.action.target, step.action.thought, step.action.raw_text]).lower(), ["find", "查找", "搜索"])
        )
        for step in history[-8:]
    )
    if not saw_find:
        return []
    saw_esc_after_find = any(
        step.action and step.action.kind == ActionKind.HOTKEY and (step.action.key or "").lower() == "esc"
        for step in history[-8:]
    )
    if saw_esc_after_find:
        return []
    return [
        "Docs structure-after-find protocol:",
        "- You used document find/search to locate the anchor for a structure task. The find popup or active search highlight may still be open.",
        "- Before inserting structure, close the find/search panel with hotkey esc once.",
        "- After Esc, operate from the visible anchor, place the caret after the full sentence including final punctuation, create a true empty body block, then continue.",
        "",
    ]


def _mentions_protocol(case: TestCase) -> list[str]:
    if not _mentions_required(case):
        return []
    return [
        "Task-specific operation protocol:",
        "- This task requires a real @ mention token.",
        "- Do not type a plain '@Name message' as normal text.",
        "- First create the mention token through the visible mention UI: type only '@' or click the visible @ button, then select the target person from the mention picker.",
        "- After the mention token is inserted, append only the remaining message text without clearing or overwriting the token.",
    ]


def _general_product_navigation_protocol(case: TestCase) -> list[str]:
    product = (case.product or "").lower()
    if product in ("docs", "im", ""):
        return []
    product_name_map = {
        "calendar": "日历/Calendar",
        "mail": "邮箱/Mail",
        "base": "多维表格/Base",
        "vc": "视频会议/VC",
    }
    display_name = product_name_map.get(product, product)
    return [
        "",
        "Product navigation protocol:",
        f"- This task targets the Feishu {display_name} module.",
        f"- If the current screenshot does NOT show the {display_name} interface, stay within the visible Feishu host and navigate to the target module.",
        "",
    ]


def _composer_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() != "im":
        return []
    return [
        "",
        "IM composer protocol:",
        "- Before sending, verify the composed content in the input area matches the task.",
        "- Do not send if the input area still contains stale text, wrong attachments, or an unfinished mention picker.",
        "",
    ]


def _docs_protocol(case: TestCase) -> list[str]:
    return [
        "",
        "Docs protocol:",
        "- Operate only within the visible Docs content area. Do not use the macOS menu bar, Dock, browser chrome, or system menus.",
        "- To create or edit document content, first focus in the Docs body, then type or use visible toolbar/insert controls.",
        "- Do not invent coordinates for invisible elements. Do not click outside the Docs document area.",
        "",
    ]


def _message_operation_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() != "im":
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not any(t in text for t in ["回复", "reply", "标记", "mark", "反应", "reaction", "表情"]):
        return []
    return [
        "",
        "Message operation protocol:",
        "- Operate on real live chat bubbles, not content depicted inside screenshots, images, or cards.",
        "- For reply/mark/reaction, first locate the exact target message bubble in the chat area, then apply the operation.",
        "",
    ]


def _attachment_share_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() != "im":
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not any(t in text for t in ["图片", "image", "文件", "file", "云文档", "分享", "share", "名片", "card"]):
        return []
    return [
        "",
        "Attachment share protocol:",
        "- Use visible send/attachment controls in the IM composer. Do not attempt to drag files.",
        "- If a file/image picker opens, select the requested item from the visible list.",
        "- Send the attachment or share card only when it is visible in the composer input area.",
        "",
    ]


def _rich_text_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() != "im":
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not any(t in text for t in ["富文本", "rich text", "加粗", "bold", "斜体", "italic"]):
        return []
    return [
        "",
        "Rich text protocol:",
        "- Use visible formatting tools in the composer toolbar.",
        "- Format the exact target text, not the entire composer content.",
        "",
    ]


def _batch_protocol(case: TestCase) -> list[str]:
    return [
        "",
        "Batch protocol:",
        "- Use Action: batch() if and only if all sub-actions are decidable from the current screenshot plus successful history.",
        "- Stop batch exactly before acting inside UI that appears only after a new popup/menu/picker/panel opens.",
        "- For batch output, add one compact JSON Actions line.",
        "",
        "Choose the next concrete GUI action from the scenario action vocabulary.",
        "Follow the scenario response format exactly: include CompletionCheck, Thought, Grounding, Action, and Expected.",
        "For batch output, include exactly one compact JSON Actions: line after Action: batch().",
        "Always include an Action: line. If the next best step is to pause, use Action: wait().",
        "Do not mention hidden verifier assertions. Do not invent coordinates for invisible targets.",
    ]


def _docs_edit_task(text: str) -> bool:
    return any(t in text for t in ["编辑", "edit", "追加", "append", "插入", "insert", "类型", "type"])


def _docs_entry_open_task(text: str) -> bool:
    return any(t in text for t in ["打开", "open", "搜索打开", "search open", "文档", "document", "未命名"])


def _docs_structure_task(text: str) -> bool:
    return any(t in text for t in ["标题", "heading", "列表", "list", "表格", "table", "分割线", "divider"])


def _docs_move_task(text: str) -> bool:
    return any(t in text for t in ["移动", "move", "段落", "paragraph"])


def _mentions_required(case: TestCase) -> bool:
    return "@" in (case.instruction or "") or "提及" in (case.instruction or "")


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def _is_docs_structure_insertion_point_text(text: str) -> bool:
    return any(t in text for t in ["end of", "末尾", "after", "段落", "paragraph", "body", "正文", "insertion", "插入点"])
