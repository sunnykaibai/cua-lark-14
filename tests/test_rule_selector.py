from cua_lark.testing.rule_selector import build_rule_selection_prompt, parse_rule_selection
from cua_lark.domain.models import TestCase


def test_rule_selector_accepts_docs_rule_modules_and_goal_contract():
    raw = "\n".join(
        [
            'RuleNeeds: ["docs_shell", "docs_body_edit", "docs_search_navigation"]',
            "Goal: open the target document and append body text",
            'CompletionEvidence: ["target document title is visible", "new body text is visible"]',
            'NonCompletionEvidence: ["text in title only"]',
            'MustNot: ["duplicate the body text"]',
            "Reason: Docs edit task needs entry, body edit, and navigation rules.",
        ]
    )

    selection = parse_rule_selection(
        raw,
        ["docs_shell", "docs_body_edit", "docs_search_navigation", "im_chat"],
        ["feishu_shell"],
    )

    assert selection.selected_rules == ["docs_shell", "docs_body_edit", "docs_search_navigation"]
    assert selection.goal_contract.goal == "open the target document and append body text"
    assert "new body text is visible" in selection.goal_contract.completion_evidence
    assert "duplicate the body text" in selection.goal_contract.must_not


def test_rule_selection_prompt_mentions_docs_rules():
    case = TestCase(
        id="DOCS-001",
        name="Docs link",
        instruction="打开文档，把指定文本设置为链接",
        expected="hidden expected",
        product="Docs",
    )

    prompt = build_rule_selection_prompt(case, [], "`docs_format_link` | Docs links | path")

    assert "docs_format_link" in prompt
    assert "links, URLs, bold, highlight" in prompt
    assert "docs_exact_span" in prompt
    assert "punctuation or suffix IDs" in prompt
    assert "Do not mix IM composer/chat rules into Docs body editing" in prompt


def test_rule_selector_accepts_docs_exact_span_module():
    raw = "\n".join(
        [
            'RuleNeeds: ["docs_shell", "docs_exact_span", "docs_format_link"]',
            "Goal: format the exact requested text span",
            'CompletionEvidence: ["exact span is linked"]',
            'NonCompletionEvidence: ["neighboring text is also linked"]',
            'MustNot: ["omit punctuation"]',
            "Reason: Exact local text selection needs punctuation-safe span rules.",
        ]
    )

    selection = parse_rule_selection(
        raw,
        ["docs_shell", "docs_exact_span", "docs_format_link", "im_chat"],
        ["feishu_shell"],
    )

    assert selection.selected_rules == ["docs_shell", "docs_exact_span", "docs_format_link"]
    assert "omit punctuation" in selection.goal_contract.must_not
