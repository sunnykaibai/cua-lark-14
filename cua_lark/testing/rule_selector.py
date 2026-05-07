from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from cua_lark.domain.models import GoalContract, StepResult, TestCase


RULE_SELECTION_SYSTEM_PROMPT = """You select operation rule modules and define a goal contract for a desktop GUI testing agent.
Use the current screenshot, task, and compact history.
Return only rule module names from the provided index.
The goal contract must be derived only from the user instruction and visible UI, not hidden expected/assertion fields.
Do not choose actions or coordinates."""


@dataclass
class RuleSelection:
    selected_rules: list[str]
    goal_contract: GoalContract = field(default_factory=GoalContract)
    reason: str = ""
    raw: str = ""
    prompt: str = ""
    reasoning: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
    fallback_used: bool = False
    error: str = ""


def build_rule_selection_prompt(case: TestCase, history: list[StepResult], rule_index: str) -> str:
    lines = [
        "# Task",
        f"instruction: {case.instruction}",
        "",
        "# Recent History",
    ]
    if not history:
        lines.append("- none")
    else:
        for step in history[-4:]:
            lines.append(_history_fact(step))
    lines.extend(
        [
            "",
            "# Rule Index",
            rule_index.strip(),
            "",
            "# Selection Rules",
            "- Select only modules needed for the current visible UI state and immediate task progress.",
            "- Include `live_object` when the screenshot contains images, cards, previews, thumbnails, or historical message evidence.",
            "- Include `screenshot_overlay` when screenshot/recording/OCR overlay or selection toolbar is visible.",
            "- Include `mention_picker` when the task or visible UI involves @ mention tokens.",
            "- Include `message_operations` when the task or visible UI involves reply, mark, or emoji reaction on messages.",
            "- Include `conversation_ops` when the task or visible UI involves unread, mark, complete/done, or status operations on conversation-list rows.",
            "- Include `search_find` when the instruction asks to find/search/locate content, such as 找到, 搜索, 查找, 最近一条包含, or contains.",
            "- For search plus chat object share/send tasks, the searchable picker/share flow should be treated as the preferred search surface.",
            "- Include `attachment_share` when the task or visible UI involves files, images, cloud documents, cards, share popups, or document search sharing.",
            "- Include `composer` and `im_chat` when a file/image/cloud document/card must be sent or shared as a message into a chat.",
            "- Include `rich_text` when the task or visible UI involves formatting such as bold text.",
            "- Include composer/chat/picker rules only when that UI state is visible or directly needed next.",
            "- Include `docs_shell` when the task or visible UI is Feishu Docs, cloud docs, document open/entry, browser-docs surfaces, or Docs popups.",
            "- Include `docs_body_edit` when the task asks to insert, append, replace, delete, paste, or edit Docs body content.",
            "- Include `docs_search_navigation` when the Docs task asks to find, locate, scroll to, open a named document, use outline/目录, or recover from a missing paragraph.",
            "- Include `docs_structure` when the Docs task involves headings, lists, task lists, tables, quote blocks, code blocks, dividers, or outline heading structure.",
            "- Include `docs_format_link` when the Docs task involves links, URLs, bold, highlight, code style, or partial phrase formatting.",
            "- Include `docs_exact_span` when the Docs task modifies a specified local text span, such as 指定文本, 局部文本, 短句, 词语, replace/delete/copy/move/link/bold/comment on exact text, especially when punctuation or suffix IDs must be preserved.",
            "- Include `docs_share_permission` when the Docs task involves sharing, permissions, collaborators, invite, or inspecting share state.",
            "- Include `docs_local_material` when the Docs task uses local Markdown/text material, pasted snippets, agenda snippets, or material references.",
            "- Do not mix IM composer/chat rules into Docs body editing unless the screenshot truly shows an IM share/send flow.",
            "- Prefer 2-5 modules. Do not select every module unless the screenshot truly needs them.",
            "",
            "# Goal Contract Rules",
            "- Define the user-visible end state for this case before action execution starts.",
            "- The contract must help the execution model decide when to return finished.",
            "- Do not use hidden validation fields or verifier assertions.",
            "- Completion evidence should identify the newest/live UI object or state that proves the task is done.",
            "- Non-completion evidence should list common false positives such as drafts, older matches, screenshots/previews, open pickers, or partial states.",
            "- MustNot should include duplicate/repeated work risks when relevant.",
            "",
            "# Output",
            "RuleNeeds: [\"rule_name\", \"rule_name\"]",
            "Goal: short user-visible goal",
            "CompletionEvidence: [\"evidence\", \"evidence\"]",
            "NonCompletionEvidence: [\"false positive\", \"false positive\"]",
            "MustNot: [\"constraint\", \"constraint\"]",
            "Reason: one short sentence",
        ]
    )
    return "\n".join(lines)


def parse_rule_selection(raw: str, available_rules: list[str], fallback_rules: list[str]) -> RuleSelection:
    available = set(available_rules)
    selected = _extract_rule_names(raw)
    filtered = []
    for name in selected:
        if name in available and name not in filtered:
            filtered.append(name)
    reason = _extract_reason(raw)
    contract = _extract_goal_contract(raw)
    if filtered:
        return RuleSelection(selected_rules=filtered, goal_contract=contract, reason=reason, raw=raw)
    return RuleSelection(
        selected_rules=list(fallback_rules),
        goal_contract=contract,
        reason=reason or "fallback to default starter rules",
        raw=raw,
        fallback_used=True,
        error="no valid RuleNeeds parsed",
    )


def _extract_rule_names(raw: str) -> list[str]:
    text = raw or ""
    match = re.search(r"RuleNeeds\s*:\s*(\[[^\n\r]+?\])", text, re.IGNORECASE | re.DOTALL)
    if match:
        parsed = _parse_list(match.group(1))
        if parsed:
            return parsed

    match = re.search(r"RuleNeeds\s*:\s*([^\n\r]+)", text, re.IGNORECASE)
    if match:
        return _split_names(match.group(1))

    match = re.search(r"rules?\s*:\s*(\[[^\n\r]+?\])", text, re.IGNORECASE | re.DOTALL)
    if match:
        parsed = _parse_list(match.group(1))
        if parsed:
            return parsed
    return []


def _parse_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return _split_names(value.strip("[]"))


def _split_names(value: str) -> list[str]:
    names = []
    for item in re.split(r"[,，\s]+", value):
        name = item.strip().strip("'\"`[]")
        if name:
            names.append(name)
    return names


def _extract_reason(raw: str) -> str:
    match = re.search(r"Reason\s*:\s*(.+)", raw or "", re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_goal_contract(raw: str) -> GoalContract:
    return GoalContract(
        goal=_extract_line(raw, "Goal"),
        completion_evidence=_extract_string_list(raw, "CompletionEvidence"),
        non_completion_evidence=_extract_string_list(raw, "NonCompletionEvidence"),
        must_not=_extract_string_list(raw, "MustNot"),
        raw=raw or "",
    )


def _extract_line(raw: str, field: str) -> str:
    match = re.search(rf"^{re.escape(field)}\s*:\s*(.+)$", raw or "", re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_string_list(raw: str, field: str) -> list[str]:
    match = re.search(rf"^{re.escape(field)}\s*:\s*(\[[^\n\r]*\])", raw or "", re.IGNORECASE | re.MULTILINE)
    if match:
        return [str(item).strip() for item in _parse_list(match.group(1)) if str(item).strip()]
    match = re.search(rf"^{re.escape(field)}\s*:\s*(.+)$", raw or "", re.IGNORECASE | re.MULTILINE)
    if not match:
        return []
    value = match.group(1).strip()
    return [item.strip("- ").strip() for item in re.split(r"[;；]", value) if item.strip()]


def _history_fact(step: StepResult) -> str:
    action = step.action
    status = "ok" if step.passed else "failed"
    parts = [f"- S{step.index}: {status}"]
    if action:
        parts.append(f"action={action.kind.value}")
        if action.target:
            parts.append(f"target={_quote(action.target)}")
        if action.text:
            parts.append(f"content={_quote(action.text)}")
        if action.key:
            parts.append(f"key={_quote(action.key)}")
    if step.message:
        parts.append(f"result={_quote(step.message)}")
    return "; ".join(parts)


def _quote(value: object) -> str:
    text = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'

