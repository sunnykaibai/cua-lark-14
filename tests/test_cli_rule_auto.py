from cua_lark.cli import _rule_names_for_args
from cua_lark.domain.models import TestCase


def test_auto_docs_rules_add_exact_span_for_local_text_tasks():
    case = TestCase(
        id="DOCS-FEAT-COMP-004",
        name="给局部文本添加链接",
        instruction="打开文档，把指定文本“DOCS-FEATURE-LINK-TARGET-8A41：目标”设置为链接",
        expected="target text is linked",
        product="Docs",
        stage="docs_realistic_composition",
    )

    names = _rule_names_for_args("auto", [case])

    assert "docs_exact_span" in names
    assert "docs_format_link" in names
    assert "docs_shell" in names


def test_auto_im_rules_do_not_add_docs_exact_span():
    case = TestCase(
        id="IM-P2-001",
        name="发送局部文本",
        instruction="给孙浩翔发送一条消息，包含指定文本",
        expected="message sent",
        product="IM",
        stage="im_chat",
    )

    names = _rule_names_for_args("auto", [case])

    assert "docs_exact_span" not in names
    assert "im_chat" in names
