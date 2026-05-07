from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from cua_lark.domain.models import CaseResult, RunInfo, Status, StepResult


def write_case(case_dir: Path, result: CaseResult) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "record.json").write_text(
        json.dumps(_json(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (case_dir / "steps.md").write_text(render_steps(result, case_dir=case_dir), encoding="utf-8")
    (case_dir / "flow.md").write_text(render_flow(result), encoding="utf-8")


def write_run(run: RunInfo, results: list[CaseResult]) -> None:
    summary = summarize(results)
    (run.root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run.root / "README.md").write_text(render_run(run, results, summary), encoding="utf-8")


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for item in results if item.status == Status.PASSED)
    failed = sum(1 for item in results if item.status == Status.FAILED)
    blocked = sum(1 for item in results if item.status == Status.BLOCKED)
    steps = sum(len(item.setup_steps) + len(item.steps) for item in results)
    duration = sum(item.duration_seconds for item in results)
    quality_warnings = sum(1 for item in results if (item.process_quality or {}).get("status") == "warning")
    grounding_checks = sum((item.process_quality or {}).get("grounding_check_count", 0) for item in results)
    grounding_corrections = sum(
        (item.process_quality or {}).get("grounding_check_corrected_count", 0) for item in results
    )
    grounding_skipped = sum((item.process_quality or {}).get("grounding_check_skipped_count", 0) for item in results)
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "success_rate": round(passed / total * 100, 2) if total else 0,
        "steps": steps,
        "duration_seconds": round(duration, 2),
        "average_duration_seconds": round(duration / total, 2) if total else 0,
        "quality_warning_cases": quality_warnings,
        "grounding_check_count": grounding_checks,
        "grounding_check_corrected_count": grounding_corrections,
        "grounding_check_skipped_count": grounding_skipped,
    }


def render_run(run: RunInfo, results: list[CaseResult], summary: dict[str, Any]) -> str:
    lines = [
        f"# {run.round_id}",
        "",
        f"- Suite: `{run.suite}`",
        f"- Started: {run.started_at}",
        f"- Cases: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Blocked: {summary['blocked']}",
        f"- Success rate: {summary['success_rate']}%",
        f"- Duration: {summary['duration_seconds']}s",
        f"- Quality warning cases: {summary['quality_warning_cases']}",
        f"- Grounding checks: {summary['grounding_check_count']}",
        f"- Grounding skipped: {summary['grounding_check_skipped_count']}",
        f"- Grounding corrections: {summary['grounding_check_corrected_count']}",
        "",
        "## Case Matrix",
        "",
        "| Case | Stage | Status | Quality | Steps | Duration | Failure |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for result in results:
        rel = f"cases/{_case_dir_from_result(result)}/steps.md"
        lines.append(
            f"| [{_md(result.case.id)}]({rel}) | {_md(result.case.stage)} | "
            f"{result.status.value} | {_quality_label(result)} | {len(result.steps)} | "
            f"{result.duration_seconds:.2f}s | {_md(result.failure)} |"
        )
    lines.extend(["", "## Failed First", ""])
    failed = [item for item in results if item.status != Status.PASSED]
    if not failed:
        lines.append("All selected cases passed.")
    for result in failed:
        lines.extend(
            [
                f"### {result.case.id} {result.case.name}",
                "",
                f"- Instruction: {_md(result.case.instruction)}",
                f"- Expected: {_md(result.case.expected)}",
                f"- Failure: {_md(result.failure)}",
                f"- Steps: `cases/{_case_dir_from_result(result)}/steps.md`",
                f"- Final screenshot: `cases/{_case_dir_from_result(result)}/{result.final_screenshot}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def render_steps(result: CaseResult, *, case_dir: Path | None = None) -> str:
    lines = [
        f"# {result.case.id} {result.case.name}",
        "",
        f"- Status: {result.status.value}",
        f"- Instruction: {result.case.instruction}",
        f"- Expected: {result.case.expected}",
        f"- Action policy source: {result.case.action_policy_source}",
        f"- Explicit allowed actions: {_md(result.case.explicit_allowed_actions)}",
        f"- Effective allowed actions: {_md(result.case.allowed_actions)}",
        f"- Failure: {result.failure}",
        f"- Final screenshot: `{result.final_screenshot}`",
        f"- Verifier: {_md(result.verifier_response)}",
        f"- Process quality: {_md(result.process_quality)}",
        f"- Mermaid flow: `flow.md`",
        f"- Setup instruction: {_md(result.case.setup_instruction)}",
        "",
        "## Goal Contract",
        "",
        _render_goal_contract(result),
        "",
        "## Timing Table",
        "",
        _render_timing_table(result),
        "",
        "## Setup Timeline",
        "",
    ]
    if result.setup_steps:
        for step in result.setup_steps:
            lines.extend(_render_step(step, case_dir=case_dir))
    else:
        lines.append("_No setup steps recorded._")
    lines.extend(
        [
            "",
            "## Test Timeline",
            "",
        ]
    )
    for step in result.steps:
        lines.extend(_render_step(step, case_dir=case_dir))
    return "\n".join(lines) + "\n"


def _render_step(step: StepResult, *, case_dir: Path | None = None) -> list[str]:
    action = step.action
    action_text = action.kind.value if action else "parse_error"
    target = action.target if action else ""
    return [
        f"### Step {step.index}",
        "",
        f"- Result: {'ok' if step.passed else 'failed'}",
        f"- Action: `{action_text}`",
        f"- Target: {_md(target)}",
        f"- Thought: {_md(action.thought if action else '')}",
        f"- Expected visible change: {_md(action.expected if action else '')}",
        f"- Message: {_md(step.message)}",
        f"- Visual change: {_md(_visual_summary(step.visual_change))}",
        f"- Capture: {_md(step.screenshot)}",
        f"- Before: `{step.before}`",
        _image("Before image", step.before, case_dir),
        f"- After: `{step.after}`",
        _image("After image", step.after, case_dir),
        f"- Grounding crop: `{step.grounding_crop}`",
        _image("Grounding crop image", step.grounding_crop, case_dir),
        f"- Elements overlay: `{step.elements_overlay}`",
        _image("Elements overlay image", step.elements_overlay, case_dir),
        f"- Elements: {_md(_elements_summary(action.grounding.get('elements') if action else []))}",
        f"- Grounding check image: `{step.grounding_check_image}`",
        _image("Grounding check annotated image", step.grounding_check_image, case_dir),
        f"- Grounding check: {_md(action.grounding_check if action else '')}",
        f"- Selected rules: {_md(', '.join(step.selected_rules))}",
        f"- Rule selection reason: {_md(step.rule_selection_reason)}",
        f"- Rule selection fallback: {_md(step.rule_selection_fallback_used)}",
        f"- Rule selection error: {_md(step.rule_selection_error)}",
        f"- Timing: {_md(step.timing)}",
        "",
        "#### Selected rules prompt",
        "",
        _code_block(step.rules_prompt),
        "",
        "#### Rule selection prompt",
        "",
        _code_block(step.rule_selection_prompt),
        "",
        "#### Rule selection raw output",
        "",
        _code_block(step.rule_selection_raw),
        "",
        "#### Execution VLM system prompt",
        "",
        _code_block(step.system_prompt),
        "",
        "#### Execution VLM prompt",
        "",
        _code_block(step.prompt),
        "",
        "#### Execution VLM raw output",
        "",
        _code_block(step.raw_model),
        "",
        "#### Grounding check VLM prompt",
        "",
        _code_block(step.grounding_check_prompt),
        "",
        "#### Grounding check VLM raw output",
        "",
        _code_block((action.grounding_check or {}).get("raw", "") if action else ""),
        "",
    ]


def render_flow(result: CaseResult) -> str:
    lines = [
        f"# {result.case.id} {result.case.name} Flow",
        "",
        f"- Status: {result.status.value}",
        f"- Duration: {result.duration_seconds:.2f}s",
        f"- Steps: {len(result.steps)}",
        "",
        "## Mermaid",
        "",
        "```mermaid",
        render_mermaid_flow(result),
        "```",
        "",
        "## Timing Table",
        "",
        _render_timing_table(result),
    ]
    return "\n".join(lines) + "\n"


def render_mermaid_flow(result: CaseResult) -> str:
    lines = [
        "flowchart TD",
        f'  START(["Start<br/>{_mermaid_text(result.case.id)}"])',
    ]
    previous = "START"
    for step in result.setup_steps:
        node_id = f"P{step.index}"
        lines.append(f'  {node_id}["setup {_step_mermaid_label(step)}"]')
        lines.append(f"  {previous} --> {node_id}")
        previous = node_id
    for step in result.steps:
        node_id = f"S{step.index}"
        lines.append(f'  {node_id}["{_step_mermaid_label(step)}"]')
        lines.append(f"  {previous} --> {node_id}")
        previous = node_id
    lines.append(f'  END(["Final<br/>{_mermaid_text(result.status.value)}<br/>{result.duration_seconds:.2f}s"])')
    lines.append(f"  {previous} --> END")
    return "\n".join(lines)


def _render_goal_contract(result: CaseResult) -> str:
    contract = result.goal_contract
    if not contract:
        return "_No goal contract recorded._"
    lines = [
        f"- Goal: {_md(contract.goal)}",
        "- Completion evidence:",
    ]
    lines.extend([f"  - {_md(item)}" for item in contract.completion_evidence] or ["  - none"])
    lines.append("- Non-completion evidence:")
    lines.extend([f"  - {_md(item)}" for item in contract.non_completion_evidence] or ["  - none"])
    lines.append("- Must not:")
    lines.extend([f"  - {_md(item)}" for item in contract.must_not] or ["  - none"])
    return "\n".join(lines)


def _render_timing_table(result: CaseResult) -> str:
    lines = [
        "| Step | Result | Action | Target | Total | VLM | Rule selection | Grounding | Execute | Capture | Report |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if not result.steps:
        return "\n".join(lines)
    for step in result.steps:
        action = step.action
        timing = step.timing or {}
        lines.append(
            f"| {step.index} | {'ok' if step.passed else 'failed'} | "
            f"{_md(action.kind.value if action else 'parse_error')} | "
            f"{_md(action.target if action else '')} | "
            f"{_seconds(timing.get('total_step_seconds'))} | "
            f"{_seconds(timing.get('main_vlm_seconds'))} | "
            f"{_seconds(timing.get('rule_selection_seconds'))} | "
            f"{_seconds(timing.get('grounding_check_seconds'))} | "
            f"{_seconds(timing.get('execute_seconds'))} | "
            f"{_seconds(_capture_seconds(timing))} | "
            f"{_seconds(timing.get('report_seconds'))} |"
        )
    return "\n".join(lines)


def _step_mermaid_label(step: StepResult) -> str:
    action = step.action
    action_text = action.kind.value if action else "parse_error"
    target = action.target if action else ""
    timing = step.timing or {}
    return _mermaid_text(
        f"S{step.index} {action_text}\n"
        f"{target}\n"
        f"{'ok' if step.passed else 'failed'} total {_seconds(timing.get('total_step_seconds'))}"
    )


def _case_dir_from_result(result: CaseResult) -> str:
    from cua_lark.testing.run_context import case_dir_name

    return case_dir_name(result.case.id, result.case.name)


def _json(value: Any) -> Any:
    if is_dataclass(value):
        return _json(asdict(value))
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", "<br>")


def _visual_summary(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value or "")
    parts = [str(value.get("status") or "unknown")]
    if value.get("mean_delta") is not None:
        parts.append(f"mean_delta={value['mean_delta']}")
    if value.get("bbox"):
        parts.append(f"bbox={value['bbox']}")
    return "; ".join(parts)


def _quality_label(result: CaseResult) -> str:
    quality = result.process_quality or {}
    status = str(quality.get("status") or "")
    warnings = quality.get("warnings") or []
    if not status:
        return ""
    if not warnings:
        return _md(status)
    return _md(f"{status}: {', '.join(warnings)}")


def _elements_summary(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return ""
    parts = []
    for index, element in enumerate(value, start=1):
        if not isinstance(element, dict):
            continue
        name = element.get("name") or "unknown"
        role = element.get("role") or ""
        bbox = element.get("box_0_1000") or ""
        point = element.get("point_0_1000") or ""
        confidence = element.get("confidence") or ""
        parts.append(f"{index}. {name} ({role}) bbox={bbox} point={point} confidence={confidence}")
    return "<br>".join(parts)


def _image(label: str, filename: str, case_dir: Path | None = None) -> str:
    if not filename:
        return f"{label}:"
    path = str(case_dir / filename) if case_dir else filename
    return f"{label}:\n![{label}]({path})"


def _code_block(value: Any) -> str:
    text = str(value or "")
    if not text:
        return "```text\n\n```"
    return "```text\n" + text.replace("```", "'''") + "\n```"


def _seconds(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number:.3f}s" if number else ""


def _capture_seconds(timing: dict[str, Any]) -> float:
    return float(timing.get("capture_before_seconds") or 0) + float(timing.get("capture_after_seconds") or 0)


def _mermaid_text(value: Any) -> str:
    text = str(value or "")
    return (
        text.replace("\\", "\\\\")
        .replace('"', "'")
        .replace("|", " ")
        .replace("[", "(")
        .replace("]", ")")
        .replace("\n", "<br/>")
    )
