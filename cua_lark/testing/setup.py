from __future__ import annotations

import re

from cua_lark.domain.models import GoalContract, StepResult, TestCase


def build_setup_step_prompt(
    case: TestCase,
    history: list[StepResult],
    *,
    rules_prompt: str = "",
    goal_contract: GoalContract | None = None,
) -> str:
    recipe = _setup_recipe(case)
    setup_expected = case.setup_expected or case.expected or "起始背景已经准备好"
    lines = [
        "Setup task:",
        case.setup_instruction or case.instruction,
        "",
        "Setup expected state:",
        setup_expected,
        "",
        "Setup mode protocol:",
        "- This is framework-controlled setup, not free-form exploration.",
        "- Follow the fixed recipe below and stop as soon as the expected state is visible.",
        "- If the expected setup state is already visible in the current screenshot, return finished immediately.",
        "- Do not invent new document creation, unrelated menus, or alternative entry routes.",
        "- Operate only on the visible Feishu/Lark/Docs content area. Do not use the macOS menu bar, Dock, browser chrome, app switcher, system menus, or window menus as setup shortcuts.",
        "- Do not repeat the same failed click twice if the screenshot did not visibly change.",
        "",
        "Setup recipe:",
    ]
    lines.extend(recipe)
    if history:
        lines.extend(
            [
                "",
                "Execution history:",
            ]
        )
        for step in history[-5:]:
            action = step.action.kind.value if step.action else "parse_error"
            target = step.action.target if step.action else ""
            thought = step.action.thought if step.action else ""
            message = step.message or ("ok" if step.passed else "failed")
            visual = step.visual_change.get("status", "unknown") if isinstance(step.visual_change, dict) else step.visual_change
            lines.append(
                f"- step {step.index}: action={action}; target={target}; thought={thought}; "
                f"execution_result={message}; observed_visual_change={visual}"
            )
    if goal_contract:
        lines.extend(_goal_contract_lines(goal_contract))
    if rules_prompt.strip():
        lines.extend(["", "Selected operation rules:", rules_prompt.strip()])
    lines.extend(
        [
            "",
            "Choose the next concrete GUI action from the scenario action vocabulary.",
            "Follow the scenario response format exactly: include CompletionCheck, Thought, Grounding, Action, and Expected.",
            "For batch output, include exactly one compact JSON Actions: line after Action: batch().",
            "Always include an Action: line. If the next best step is to pause, use Action: wait().",
            "Do not mention hidden verifier assertions.",
        ]
    )
    return "\n".join(lines)


def _setup_recipe(case: TestCase) -> list[str]:
    case_id = _original_case_id(case.id)
    setup_instruction = case.setup_instruction or case.instruction
    setup_expected = case.setup_expected or case.expected
    target_title = _extract_title(setup_expected) or _extract_title(setup_instruction)
    quoted_titles = _extract_quoted_titles(setup_instruction)
    decoy_title = quoted_titles[1] if len(quoted_titles) > 1 else ""

    if case_id == "DOCS-ENTRY-PROVISION-001":
        return [
            "- Goal: confirm the dedicated entry target document exists and is opened.",
            f"- Target title: {target_title or 'CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET'}",
            "- If the exact target title is already visible, return finished immediately.",
            "- Otherwise, use the visible Feishu app Docs/cloud-document entry surface, search the exact full target title once, open the matching result, and stop as soon as the title becomes visible.",
            "- Do not create a new document.",
        ]
    if case_id == "DOCS-ENTRY-001":
        return [
            "- Goal: leave the current target document and land on any visible Feishu surface that is not the target document.",
            f"- Target title to leave: {target_title or 'CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET'}",
            "- If the target document is already visible, switch away from it using a visible Docs home, list, breadcrumb, app shell, or Feishu surface until the target page is no longer the active page.",
            "- Do not create a document and do not search for a different document.",
            "- Finish when a visible Feishu or Docs non-target surface is shown.",
        ]
    if case_id == "DOCS-ENTRY-002":
        return [
            "- Goal: land on the Feishu cloud-document home or recent-home surface.",
            f"- Target title to keep available: {target_title or 'CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET'}",
            "- If the home or recent surface is already visible, return finished immediately.",
            "- Otherwise, use the visible Feishu app Docs/cloud-document entry surface and stop once the home/recent surface is visible.",
            "- Do not open a document body as the final setup state.",
        ]
    if case_id == "DOCS-ENTRY-003":
        return [
            "- Goal: open the non-target decoy document and keep it active.",
            f"- Target title to avoid: {target_title or 'CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET'}",
            f"- Decoy title to open: {decoy_title or 'CUA-Lark Docs 入口鲁棒性非目标文档 DOCS-ENTRY-DECOY'}",
            "- If the decoy document is already visible, return finished immediately.",
            "- Otherwise, use the Feishu app Docs/cloud-document entry surface, search the exact full decoy title once, open the matching result, and stop when the decoy title is visible.",
            "- Do not create a new document and do not leave the setup on the target document.",
        ]
    if case_id == "DOCS-ENTRY-004":
        return [
            "- Goal: land on a browser-hosted Feishu Docs home, recent-home, or search surface.",
            f"- Target title to keep available for the later test: {target_title or 'CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET'}",
            "- If a browser Feishu Docs home/search surface is already visible, return finished immediately.",
            "- Otherwise, use the browser Docs route only and stop once the browser-hosted Docs home/recent/search surface is visible.",
            "- Do not switch this setup to the desktop Feishu app.",
        ]
    if case_id == "DOCS-ENTRY-005":
        return [
            "- Goal: keep the exact target document already opened and visible.",
            f"- Target title: {target_title or 'CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET'}",
            "- If the exact target document title is already visible in the title, breadcrumb, or main content area, return finished immediately.",
            "- Otherwise, open the exact target document with the shortest visible Docs route and stop as soon as the title becomes visible.",
            "- Do not switch away to another document.",
        ]
    if case_id == "DOCS-ENTRY-006":
        return [
            "- Goal: open the exact target document and then leave one real Docs overlay visible on top of it.",
            f"- Target title: {target_title or 'CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET'}",
            "- If the target document is visible but no overlay is present, open one real Docs overlay such as share, search, more, or permissions, and stop.",
            "- If the overlay is already visible over the target document, return finished immediately.",
            "- Do not use a fake overlay drawn inside the document body.",
        ]
    return [
        "- Goal: prepare the requested setup state as described by the setup instruction.",
        "- Use the shortest visible route that makes the setup_expected text true.",
    ]


def _goal_contract_lines(goal_contract: GoalContract | None) -> list[str]:
    if not goal_contract:
        return []
    lines = ["", "Goal contract:"]
    if goal_contract.goal:
        lines.append(f"- Goal: {goal_contract.goal}")
    if goal_contract.completion_evidence:
        lines.append("- Completion evidence: " + "; ".join(goal_contract.completion_evidence))
    if goal_contract.non_completion_evidence:
        lines.append("- Non-completion evidence: " + "; ".join(goal_contract.non_completion_evidence))
    if goal_contract.must_not:
        lines.append("- Must not: " + "; ".join(goal_contract.must_not))
    return lines


def _original_case_id(case_id: str) -> str:
    if case_id.endswith("-SETUP"):
        return case_id.removesuffix("-SETUP")
    return case_id


def _extract_title(text: str) -> str:
    titles = _extract_quoted_titles(text)
    return titles[0] if titles else ""


def _extract_quoted_titles(text: str) -> list[str]:
    if not text:
        return []
    pattern = r"[“\"]([^”\"]+)[”\"]"
    return [match.strip() for match in re.findall(pattern, text) if match.strip()]
