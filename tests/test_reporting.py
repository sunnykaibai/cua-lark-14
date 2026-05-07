from pathlib import Path

from cua_lark.domain.models import Action, ActionKind, CaseResult, Status, StepResult, TestCase
from cua_lark.reporting.writer import write_case, write_run
from cua_lark.testing.run_context import RunInfo


def test_report_writer_creates_review_files(tmp_path: Path):
    case = TestCase(
        id="C-001",
        name="demo",
        instruction="do it",
        expected="done",
        allowed_actions=["click", "type_text"],
        explicit_allowed_actions=["click"],
        action_policy_source="merged",
    )
    result = CaseResult(
        case=case,
        status=Status.PASSED,
        duration_seconds=1.2,
        steps=[
            StepResult(
                index=1,
                action=Action(
                    kind=ActionKind.CLICK,
                    target="send button",
                    grounding={
                        "elements": [
                            {
                                "name": "send button",
                                "role": "action_target",
                                "box_0_1000": [900, 900, 950, 950],
                                "point_0_1000": [925, 925],
                                "confidence": "0.90",
                            }
                        ]
                    },
                ),
                before="01-before.png",
                after="01-after.png",
                elements_overlay="01-elements.png",
                system_prompt="system rules",
                prompt="Task:\ndo it",
                raw_model="Action: click(point='<point>1 2</point>')",
            )
        ],
    )
    case_dir = tmp_path / "cases" / "C-001__demo"
    write_case(case_dir, result)
    run = RunInfo("suite", "round-1", tmp_path, tmp_path / "cases", "now")
    write_run(run, [result])

    assert (case_dir / "record.json").exists()
    steps = (case_dir / "steps.md").read_text(encoding="utf-8")
    assert "Action policy source: merged" in steps
    assert "Effective allowed actions" in steps
    assert f"Before image:\n![Before image]({case_dir / '01-before.png'})" in steps
    assert "#### Execution VLM system prompt" in steps
    assert "system rules" in steps
    assert "#### Execution VLM prompt" in steps
    assert "Task:\ndo it" in steps
    assert "Action: click" in steps
    assert f"Elements overlay image:\n![Elements overlay image]({case_dir / '01-elements.png'})" in steps
    assert "send button (action_target)" in steps
    assert "Success rate" in (tmp_path / "README.md").read_text(encoding="utf-8")
