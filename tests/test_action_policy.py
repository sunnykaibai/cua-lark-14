from pathlib import Path

from cua_lark.domain.models import TestCase
from cua_lark.testing.action_policy import infer_allowed_actions
from cua_lark.testing.cases import load_cases


def test_docs_external_case_without_allowed_actions_gets_inferred_exact_span_actions(tmp_path: Path):
    cases_file = tmp_path / "external-docs.yaml"
    cases_file.write_text(
        """
test_cases:
  - id: EXT-DOCS-001
    product: Docs
    name: 外部链接样例
    test_stage: challenge_docs
    instruction: 打开文档，把文本“DOCS-EXT-LINK-TARGET”设置为链接
    expected: 目标文本呈现为链接
""".strip(),
        encoding="utf-8",
    )

    case = load_cases(cases_file)[0]

    assert case.explicit_allowed_actions == []
    assert case.action_policy_source == "inferred"
    assert "click" in case.allowed_actions
    assert "drag" in case.allowed_actions
    assert "batch" in case.allowed_actions


def test_docs_explicit_allowed_actions_are_merged_with_inferred_policy(tmp_path: Path):
    cases_file = tmp_path / "explicit-docs.yaml"
    cases_file.write_text(
        """
test_cases:
  - id: EXT-DOCS-002
    product: Docs
    name: 外部复制样例
    test_stage: challenge_docs
    instruction: 复制指定文本“DOCS-EXT-COPY”到目标锚点后
    expected: 目标锚点后出现复制文本
    allowed_actions: [click, type_text]
""".strip(),
        encoding="utf-8",
    )

    case = load_cases(cases_file)[0]

    assert case.explicit_allowed_actions == ["click", "type_text"]
    assert case.action_policy_source == "merged"
    assert "drag" in case.allowed_actions
    assert "batch" in case.allowed_actions


def test_im_external_reply_case_gets_right_click_policy():
    case = TestCase(
        id="EXT-IM-001",
        product="IM",
        name="回复指定消息",
        instruction="回复最近一条消息并发送收到",
        expected="出现带引用的回复",
    )

    actions = infer_allowed_actions(case)

    assert "right_click" in actions
    assert "type_text" in actions


def test_plain_external_docs_yaml_can_infer_product_and_actions(tmp_path: Path):
    cases_file = tmp_path / "plain-docs.yaml"
    cases_file.write_text(
        """
test_cases:
  - id: PLAIN-001
    instruction: 在飞书云文档中把文本“DOCS-PLAIN-TARGET”加粗
    expected: 目标文本已经加粗
""".strip(),
        encoding="utf-8",
    )

    case = load_cases(cases_file)[0]

    assert case.product == "Docs"
    assert case.action_policy_source == "inferred"
    assert "drag" in case.allowed_actions
    assert "batch" in case.allowed_actions


def test_docs_comment_case_uses_toolbar_path_without_inferred_right_click():
    case = TestCase(
        id="EXT-DOCS-COMMENT-001",
        product="Docs",
        name="给指定文本添加评论",
        instruction="选中文本 DOCS-COMMENT-TARGET 并添加评论",
        expected="目标文本旁出现评论",
    )

    actions = infer_allowed_actions(case)

    assert "drag" in actions
    assert "click" in actions
    assert "right_click" not in actions


def test_plain_external_im_yaml_can_infer_product_and_actions(tmp_path: Path):
    cases_file = tmp_path / "plain-im.yaml"
    cases_file.write_text(
        """
test_cases:
  - id: PLAIN-IM-001
    instruction: 在飞书消息里回复最近一条消息并发送“收到”
    expected: 出现带引用的回复消息
""".strip(),
        encoding="utf-8",
    )

    case = load_cases(cases_file)[0]

    assert case.product == "IM"
    assert case.action_policy_source == "inferred"
    assert "right_click" in case.allowed_actions


def test_docs_table_case_gets_drag_for_dirty_table_cleanup():
    case = TestCase(
        id="DOCS-FEAT-COMP-001",
        product="Docs",
        name="插入三列表格",
        instruction="在目标锚点后插入一个三列表格",
        expected="锚点后出现真实表格",
    )

    actions = infer_allowed_actions(case)

    assert "drag" in actions
    assert "batch" in actions
