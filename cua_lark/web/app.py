from __future__ import annotations

import json
import threading
import time
import traceback
from pathlib import Path
from typing import Any

import gradio as gr
import yaml

from cua_lark.adapters.gui import PyAutoGui
from cua_lark.adapters.screen import PyAutoGuiScreen
from cua_lark.adapters.vlm import build_vlm
from cua_lark.domain.models import TestCase
from cua_lark.runtime.config import NEW_ROOT, load_settings
from cua_lark.testing.cases import load_cases
from cua_lark.testing.run_context import case_dir_name, create_run
from cua_lark.testing.runner import CaseRunner

SCENARIO_DIR = NEW_ROOT / "cua_lark" / "scenarios"
TEST_CASES_DIR = NEW_ROOT / "tests" / "test_cases"
RESULTS_ROOT = NEW_ROOT / "results"

_cancel_event: threading.Event | None = None
_run_lock = threading.Lock()


def _request_stop():
    global _cancel_event
    if _cancel_event is not None:
        _cancel_event.set()


def _list_yaml_files() -> list[str]:
    if not TEST_CASES_DIR.exists():
        return []
    return sorted(p.name for p in TEST_CASES_DIR.glob("*.yaml"))


def _list_scenario_files() -> list[str]:
    if not SCENARIO_DIR.exists():
        return []
    return sorted(p.name for p in SCENARIO_DIR.glob("*.md"))


def _load_system_prompt() -> str:
    from cua_lark.runtime.config import NEW_ROOT
    path = NEW_ROOT / "cua_lark" / "scenarios" / "system.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _load_scenario_prompts() -> dict[str, str]:
    prompts: dict[str, str] = {}
    if SCENARIO_DIR.exists():
        for path in sorted(SCENARIO_DIR.glob("*.md")):
            key = path.stem
            prompts[key] = path.read_text(encoding="utf-8")
    return prompts


def _get_stages_from_yaml(yaml_file: str) -> list[str]:
    path = TEST_CASES_DIR / yaml_file
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return []
    stages = data.get("test_stages") or []
    return [s["id"] for s in stages if isinstance(s, dict) and "id" in s]


def _get_cases_from_yaml(yaml_file: str, stage: str | None = None) -> list[dict[str, str]]:
    path = TEST_CASES_DIR / yaml_file
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return []
    raw_cases = data.get("test_cases") or []
    if not isinstance(raw_cases, list):
        return []

    stage_case_ids: set[str] = set()
    if stage:
        for s in data.get("test_stages") or []:
            if isinstance(s, dict) and s.get("id") == stage:
                stage_case_ids.update(str(c) for c in (s.get("cases") or []))

    result = []
    for c in raw_cases:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id", ""))
        if stage and stage_case_ids and cid not in stage_case_ids:
            continue
        result.append({
            "id": cid,
            "name": str(c.get("name", cid)),
            "instruction": str(c.get("instruction", "")),
            "expected": str(c.get("expected", "")),
            "product": str(c.get("product", "")),
            "stage": str(c.get("test_stage", "")),
        })
    return result


def _build_runner(
    system_prompt: str,
    max_steps: int,
    grounding_check: bool,
    capture_mode: str,
    backend_name: str,
) -> CaseRunner:
    settings = load_settings()
    app_names = list((settings.screenshot.get("app_names") or []) or ["飞书", "Feishu", "Lark"])
    browser_app_names = list((settings.screenshot.get("browser_app_names") or []) or ["Safari", "Google Chrome", "Chrome", "Arc"])
    browser_title_keywords = list(
        (settings.screenshot.get("browser_title_keywords") or []) or ["feishu.cn", "larksuite.com", "飞书云文档", "未命名文档"]
    )
    app_recovery_names = list(
        (settings.screenshot.get("app_recovery_names") or []) or ["飞书", "Feishu", "Lark", "Safari", "Google Chrome"]
    )

    screen = PyAutoGuiScreen(
        prefer_app_window=capture_mode == "app",
        app_names=app_names,
        browser_app_names=browser_app_names,
        browser_title_keywords=browser_title_keywords,
        prefer_browser_docs=True,
        require_app_window=False,
        app_recovery_names=app_recovery_names,
        recovery_attempts=int(settings.screenshot.get("recovery_attempts") or 2),
    )
    gui = PyAutoGui(settings)
    vlm = build_vlm(settings, backend_name if backend_name else None)

    return CaseRunner(
        screen=screen,
        gui=gui,
        vlm=vlm,
        system_prompt=system_prompt,
        max_steps=max_steps,
        final_verify=False,
        grounding_check=grounding_check,
        grounding_check_mode="high-risk",
        backend_name=backend_name or "",
        vlm_call_options=dict(settings.vlm.get("call_profiles") or {}),
        skip_setup=False,
        activate_feishu_host=True,
    )


def _build_case_from_custom_input(
    case_id: str,
    instruction: str,
    expected: str,
    product: str,
) -> TestCase:
    return TestCase(
        id=case_id,
        name=case_id,
        instruction=instruction,
        expected=expected,
        product=product,
        phase="custom",
        stage="custom",
        verification={"method": "final_visual_semantic", "assertion": expected},
        allowed_actions=["click", "type_text", "hotkey", "wait", "scroll", "double_click", "right_click", "drag", "batch"],
    )


def _run_single_case(
    runner: CaseRunner,
    case: TestCase,
    round_name: str,
) -> dict[str, Any]:
    run = create_run(RESULTS_ROOT, "cua-lark-web", round_name)
    result = runner.run(case, run.cases_dir)
    return {
        "round_id": run.round_id,
        "round_root": str(run.root),
        "case_id": result.case.id,
        "case_name": result.case.name,
        "status": result.status.value,
        "failure": result.failure or "",
        "duration": result.duration_seconds,
        "steps": [
            {
                "index": s.index,
                "action": s.action.kind.value if s.action else "none",
                "target": s.action.target if s.action else "",
                "thought": s.action.thought if s.action else "",
                "message": s.message,
                "passed": s.passed,
                "before": str(run.cases_dir / case_dir_name(case.id, case.name) / s.before) if s.before else "",
                "after": str(run.cases_dir / case_dir_name(case.id, case.name) / s.after) if s.after else "",
            }
            for s in result.steps
        ],
        "final_screenshot": str(
            run.cases_dir / case_dir_name(case.id, case.name) / result.final_screenshot
        ) if result.final_screenshot else "",
        "verifier_response": result.verifier_response or "",
    }


def _status_banner(status: str, duration: float, steps: int, failure: str = "") -> str:
    if status == "passed":
        bg = "linear-gradient(135deg, #10b981, #059669)"
        icon = "✅"
        text = "测试通过"
    elif status == "failed":
        bg = "linear-gradient(135deg, #ef4444, #dc2626)"
        icon = "❌"
        text = "测试失败"
    elif status == "blocked":
        bg = "linear-gradient(135deg, #f59e0b, #d97706)"
        icon = "🚫"
        text = "测试阻塞"
    else:
        bg = "linear-gradient(135deg, #6b7280, #4b5563)"
        icon = "⏳"
        text = f"测试结束 ({status})"

    detail = f"{duration:.1f}s · {steps} 步"
    if failure:
        detail += f" · {failure[:80]}"

    return (
        f'<div style="'
        f'background: {bg}; color: #fff; padding: 20px 24px; border-radius: 12px;'
        f'font-size: 20px; font-weight: 700; text-align: center; margin-bottom: 20px;'
        f'box-shadow: 0 4px 24px rgba(0,0,0,0.25); letter-spacing: 0.02em;'
        f'">'
        f'{icon} {text}'
        f'<div style="font-size: 14px; font-weight: 400; opacity: 0.85; margin-top: 6px;">'
        f'{detail}</div>'
        f'</div>'
    )


def run_custom_instruction(
    instruction: str,
    expected: str,
    product: str,
    max_steps: int,
    grounding_check: bool,
    capture_mode: str,
    backend: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, str, str]:
    global _cancel_event

    if not instruction.strip():
        return "", "### 请输入指令", ""

    if not _run_lock.acquire(blocking=False):
        return "", "### 已有测试在运行中，请等待完成或点击中止", ""
    _cancel_event = threading.Event()
    try:
        progress(0.1, desc="加载配置...")
        system_prompt = _load_system_prompt()

        progress(0.2, desc="构建 Runner...")
        runner = _build_runner(
            system_prompt,
            int(max_steps), grounding_check, capture_mode, backend,
        )
        runner.cancel_event = _cancel_event

        case = _build_case_from_custom_input(
            case_id="WEB-CUSTOM",
            instruction=instruction.strip(),
            expected=expected.strip(),
            product=product,
        )

        progress(0.3, desc="执行中...")
        round_name = f"web-{time.strftime('%m%d-%H%M')}"
        result = _run_single_case(runner, case, round_name)
    except Exception as exc:
        traceback.print_exc()
        return "", f"### 执行出错\n```\n{exc}\n```", ""
    finally:
        _run_lock.release()

    progress(1.0, desc="完成")

    banner = _status_banner(
        result["status"], result["duration"], len(result["steps"]), result.get("failure", ""),
    )

    if result["status"] == "passed":
        gr.Info("✅ 测试通过！", duration=10)
    elif result["status"] == "failed":
        gr.Warning("❌ 测试失败", duration=10)
    else:
        gr.Info(f"测试结束 ({result['status']})", duration=10)

    summary = banner + f"""### 执行详情

| 项目 | 值 |
|------|-----|
| 状态 | **{result['status']}** |
| 耗时 | {result['duration']:.2f}s |
| 步数 | {len(result['steps'])} |
| 轮次 | {result['round_id']} |
"""

    if result["failure"]:
        summary += f"\n**失败原因**: {result['failure']}\n"

    steps_md = "## 执行步骤\n\n"
    for s in result["steps"]:
        icon = "✅" if s["passed"] else "❌"
        steps_md += f"### Step {s['index']} {icon}\n"
        steps_md += f"- **动作**: `{s['action']}`\n"
        if s["target"]:
            steps_md += f"- **目标**: {s['target']}\n"
        if s["thought"]:
            steps_md += f"- **思路**: {s['thought']}\n"
        steps_md += f"- **消息**: {s['message']}\n"

        if s["before"]:
            steps_md += f"- **操作前截图**: `{s['before']}`\n"
        if s["after"]:
            steps_md += f"- **操作后截图**: `{s['after']}`\n"
        steps_md += "\n"

    if result["verifier_response"]:
        steps_md += f"## 最终验证\n\n{result['verifier_response']}\n"

    final_path = result.get("final_screenshot", "")
    return summary, steps_md, final_path


def run_selected_case(
    yaml_file: str,
    stage: str,
    max_steps: int,
    grounding_check: bool,
    capture_mode: str,
    backend: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, str, str]:
    global _cancel_event

    if not yaml_file:
        return "", "### 请先选择用例文件", ""

    if not _run_lock.acquire(blocking=False):
        return "", "### 已有测试在运行中，请等待完成或点击中止", ""
    _cancel_event = threading.Event()
    try:
        progress(0.1, desc="加载用例...")
        cases = load_cases(TEST_CASES_DIR / yaml_file, stages=[stage] if stage else None)
        if not cases:
            return "", f"### 未找到匹配的用例 (文件: {yaml_file}, 阶段: {stage})", ""

        progress(0.2, desc="加载配置...")
        system_prompt = _load_system_prompt()

        progress(0.3, desc="构建 Runner...")
        runner = _build_runner(
            system_prompt,
            int(max_steps), grounding_check, capture_mode, backend,
        )
        runner.cancel_event = _cancel_event

        all_summaries = []
        all_steps = []
        all_finals = []
        pass_count = 0
        fail_count = 0
        block_count = 0

        total = len(cases)
        for idx, case in enumerate(cases):
            if _cancel_event.is_set():
                all_summaries.append(f"| - | - | **cancelled** | - | - |")
                break
            progress(0.3 + 0.6 * (idx + 1) / total, desc=f"执行 {case.id} ({idx+1}/{total})...")
            round_name = f"web-{case.id.lower()}-{time.strftime('%m%d-%H%M')}"
            try:
                result = _run_single_case(runner, case, round_name)
            except Exception as exc:
                traceback.print_exc()
                all_summaries.append(f"| {case.id} | {case.name} | **error** | - | - |")
                fail_count += 1
                continue

            status = result["status"]
            if status == "passed":
                pass_count += 1
            elif status == "failed":
                fail_count += 1
            elif status == "blocked":
                block_count += 1
            else:
                fail_count += 1

            all_summaries.append(
                f"| {result['case_id']} | {result['case_name']} | **{status}** | {result['duration']:.2f}s | {len(result['steps'])} 步 |"
            )
            case_steps = f"## {result['case_id']} {result['case_name']}\n\n"
            for s in result["steps"]:
                icon = "✅" if s["passed"] else "❌"
                case_steps += f"### Step {s['index']} {icon}\n"
                case_steps += f"- **动作**: `{s['action']}`\n"
                if s["target"]:
                    case_steps += f"- **目标**: {s['target']}\n"
                if s["thought"]:
                    case_steps += f"- **思路**: {s['thought']}\n"
                case_steps += f"- **消息**: {s['message']}\n"
                if s["before"]:
                    case_steps += f"- **操作前**: `{s['before']}`\n"
                if s["after"]:
                    case_steps += f"- **操作后**: `{s['after']}`\n"
                case_steps += "\n"
            all_steps.append(case_steps)
            if result.get("final_screenshot"):
                all_finals.append(result["final_screenshot"])
    finally:
        _run_lock.release()

    header = "| 用例ID | 名称 | 状态 | 耗时 | 步数 |\n|--------|------|------|------|------|\n"

    total_duration = sum(
        float(r.split("|")[3].strip().rstrip("s").replace("s", ""))
        for r in all_summaries if "|" in r and "error" not in r
    )
    total_steps = sum(
        int(r.split("|")[4].strip().split(" ")[0])
        for r in all_summaries if "|" in r and "error" not in r and "步" in r
    )

    all_passed = fail_count == 0 and block_count == 0
    if all_passed:
        overall_status = "passed"
        toast_msg = f"✅ 全部通过！({pass_count}/{total})"
        gr.Info(toast_msg, duration=10)
    elif pass_count > 0:
        overall_status = "failed"
        toast_msg = f"⚠️ 部分通过 ({pass_count}/{total} 通过, {fail_count} 失败)"
        gr.Warning(toast_msg, duration=10)
    else:
        overall_status = "failed"
        toast_msg = f"❌ 全部失败 ({fail_count}/{total})"
        gr.Warning(toast_msg, duration=10)

    failure_text = ""
    if fail_count > 0 or block_count > 0:
        failure_text = f"{pass_count} 通过 / {fail_count} 失败 / {block_count} 阻塞"

    banner = _status_banner(overall_status, total_duration, total_steps, failure_text)

    summary = banner + "### 执行结果\n\n" + header + "\n".join(all_summaries)
    steps_text = "\n".join(all_steps)
    final_img = all_finals[-1] if all_finals else ""

    return summary, steps_text, final_img


def on_yaml_select(yaml_file: str) -> tuple:
    stages = _get_stages_from_yaml(yaml_file)
    stage_choices = stages if stages else []
    return (
        gr.update(choices=stage_choices, value=stage_choices[0] if stage_choices else None),
        "",
        "",
    )


def on_stage_select(yaml_file: str, stage: str) -> str:
    if not yaml_file or not stage:
        return "*请选择用例文件和阶段*"
    cases = _get_cases_from_yaml(yaml_file, stage)
    if not cases:
        return "*该阶段下无匹配用例*"
    lines = ["| ID | 名称 | 指令 | 预期 |", "|----|------|------|------|"]
    for c in cases:
        lines.append(f"| {c['id']} | {c['name']} | {c['instruction'][:60]} | {c['expected'][:60]} |")
    return "\n".join(lines)


APP_CSS = """
.main-container { max-width: 960px; margin: 0 auto; }
.result-box { max-height: 600px; overflow-y: auto; }
footer { display: none !important; }
"""


def _build_app() -> gr.Blocks:
    yaml_files = _list_yaml_files()
    default_yaml = yaml_files[0] if yaml_files else ""

    with gr.Blocks(title="CUA-Lark 测试控制台") as app:
        gr.Markdown(
            "# CUA-Lark 测试控制台\n"
            "纯视觉 Computer-Use Agent 测试框架 — 输入自然语言指令，让 VLM 驱动 GUI 操作。"
        )

        with gr.Tabs():
            with gr.TabItem("✏️ 指令输入"):
                gr.Markdown("### 输入自然语言指令，自动构建并运行测试")

                with gr.Row():
                    with gr.Column(scale=3):
                        instruction_input = gr.Textbox(
                            label="用户指令 (instruction)",
                            placeholder="例如：给孙浩翔发送消息「你好，这是一条测试消息」",
                            lines=3,
                        )
                        expected_input = gr.Textbox(
                            label="预期结果 (expected)",
                            placeholder="例如：与孙浩翔的聊天记录中出现消息「你好，这是一条测试消息」",
                            lines=2,
                        )
                    with gr.Column(scale=1):
                        product_select = gr.Dropdown(
                            label="产品",
                            choices=["IM", "Docs", "Calendar", "Mail"],
                            value="IM",
                        )
                        max_steps_custom = gr.Slider(
                            label="最大步数",
                            minimum=3,
                            maximum=30,
                            value=12,
                            step=1,
                        )

                with gr.Row():
                    grounding_check_custom = gr.Checkbox(label="坐标安全检查 (grounding-check)", value=False)
                    capture_mode_custom = gr.Radio(
                        label="截图模式",
                        choices=["app", "full"],
                        value="app",
                    )
                    backend_custom = gr.Dropdown(
                        label="VLM 后端",
                        choices=["seed-2.0", "minimax"],
                        value="seed-2.0",
                    )

                with gr.Row():
                    run_custom_btn = gr.Button("▶️ 运行测试", variant="primary", size="lg")
                    stop_custom_btn = gr.Button("⏹ 中止", variant="stop", size="lg")

                gr.Markdown("---")
                with gr.Row():
                    with gr.Column():
                        custom_summary = gr.Markdown("", elem_classes="result-box")
                    with gr.Column():
                        custom_steps = gr.Markdown("", elem_classes="result-box")
                custom_final_image = gr.Image(label="最终截图", visible=True, interactive=False)

                run_custom_event = run_custom_btn.click(
                    fn=run_custom_instruction,
                    inputs=[
                        instruction_input, expected_input, product_select,
                        max_steps_custom, grounding_check_custom,
                        capture_mode_custom, backend_custom,
                    ],
                    outputs=[custom_summary, custom_steps, custom_final_image],
                )
                stop_custom_btn.click(fn=_request_stop).then(fn=None, cancels=[run_custom_event])

            with gr.TabItem("📋 用例选择"):
                gr.Markdown("### 从已有 YAML 用例文件中选择并运行")

                with gr.Row():
                    yaml_select = gr.Dropdown(
                        label="用例文件",
                        choices=yaml_files,
                        value=default_yaml,
                    )
                    stage_select = gr.Dropdown(
                        label="测试阶段 (stage)",
                        choices=[],
                        value=None,
                    )

                with gr.Row():
                    max_steps_yaml = gr.Slider(
                        label="最大步数",
                        minimum=3,
                        maximum=30,
                        value=12,
                        step=1,
                    )

                with gr.Row():
                    grounding_check_yaml = gr.Checkbox(label="坐标安全检查", value=False)
                    capture_mode_yaml = gr.Radio(
                        label="截图模式",
                        choices=["app", "full"],
                        value="app",
                    )
                    backend_yaml = gr.Dropdown(
                        label="VLM 后端",
                        choices=["seed-2.0", "minimax"],
                        value="seed-2.0",
                    )

                case_preview = gr.Markdown("*请选择用例文件和阶段后查看详情*")

                with gr.Row():
                    run_yaml_btn = gr.Button("▶️ 运行选中用例", variant="primary", size="lg")
                    stop_yaml_btn = gr.Button("⏹ 中止", variant="stop", size="lg")

                gr.Markdown("---")
                with gr.Row():
                    with gr.Column():
                        yaml_summary = gr.Markdown("", elem_classes="result-box")
                    with gr.Column():
                        yaml_steps = gr.Markdown("", elem_classes="result-box")
                yaml_final_image = gr.Image(label="最终截图", visible=True, interactive=False)

                yaml_select.change(
                    fn=on_yaml_select,
                    inputs=[yaml_select],
                    outputs=[stage_select, case_preview, yaml_summary, yaml_steps],
                )
                stage_select.change(
                    fn=on_stage_select,
                    inputs=[yaml_select, stage_select],
                    outputs=[case_preview],
                )
                run_yaml_event = run_yaml_btn.click(
                    fn=run_selected_case,
                    inputs=[
                        yaml_select, stage_select,
                        max_steps_yaml, grounding_check_yaml,
                        capture_mode_yaml, backend_yaml,
                    ],
                    outputs=[yaml_summary, yaml_steps, yaml_final_image],
                )
                stop_yaml_btn.click(fn=_request_stop).then(fn=None, cancels=[run_yaml_event])

            with gr.TabItem("⚙️ 配置"):
                gr.Markdown("### 当前配置概览")
                settings = load_settings()
                config_text = json.dumps({
                    "vlm": {
                        "default_backend": settings.vlm.get("default_backend", ""),
                        "model": settings.vlm.get("seed_2_0", {}).get("model", ""),
                        "base_url": settings.vlm.get("seed_2_0", {}).get("base_url", ""),
                    },
                    "screenshot": {
                        "format": settings.screenshot.get("format", ""),
                        "prefer_app_window": settings.screenshot.get("prefer_app_window", True),
                        "app_names": settings.screenshot.get("app_names", []),
                    },
                    "executor": {
                        "operation_delay": settings.executor.get("operation_delay", 0.8),
                        "mouse_move_duration": settings.executor.get("mouse_move_duration", 0.2),
                        "type_interval": settings.executor.get("type_interval", 0.05),
                    },
                }, ensure_ascii=False, indent=2)
                gr.Code(value=config_text, language="json", label="当前配置 (config.yaml)", interactive=False)

                gr.Markdown("---")
                gr.Markdown("### 场景规则预览")
                scenario_choice = gr.Dropdown(
                    label="选择场景",
                    choices=_list_scenario_files(),
                    value="general.md",
                )
                scenario_text = gr.Markdown("")
                scenario_choice.change(
                    fn=lambda f: (SCENARIO_DIR / f).read_text(encoding="utf-8") if (SCENARIO_DIR / f).exists() else "",
                    inputs=[scenario_choice],
                    outputs=[scenario_text],
                )

            with gr.TabItem("📊 结果浏览"):
                gr.Markdown("### 浏览历史测试结果")
                results_list = _list_recent_results()
                if results_list:
                    result_choice = gr.Dropdown(
                        label="选择结果轮次",
                        choices=results_list,
                        value=results_list[0] if results_list else None,
                    )
                    result_content = gr.Markdown("", elem_classes="result-box")
                    result_images = gr.Gallery(
                        label="截图",
                        show_label=True,
                        columns=3,
                        rows=2,
                        height="auto",
                    )

                    result_choice.change(
                        fn=_load_result,
                        inputs=[result_choice],
                        outputs=[result_content, result_images],
                    )
                else:
                    gr.Markdown("*暂无历史结果，运行一次测试后将在此显示。*")

    return app


def _list_recent_results() -> list[str]:
    if not RESULTS_ROOT.exists():
        return []
    dirs = sorted(
        [d.name for d in RESULTS_ROOT.iterdir() if d.is_dir()],
        reverse=True,
    )
    return dirs[:20]


def _load_result(round_dir: str) -> tuple[str, list[str]]:
    readme = RESULTS_ROOT / round_dir / "README.md"
    summary_json = RESULTS_ROOT / round_dir / "summary.json"

    text_parts = []
    if readme.exists():
        text_parts.append(readme.read_text(encoding="utf-8"))
    elif summary_json.exists():
        data = json.loads(summary_json.read_text(encoding="utf-8"))
        text_parts.append(f"### {round_dir}\n\n")
        text_parts.append(f"- 总数: {data.get('total', 0)}\n")
        text_parts.append(f"- 通过: {data.get('passed', 0)}\n")
        text_parts.append(f"- 失败: {data.get('failed', 0)}\n")
        text_parts.append(f"- 阻塞: {data.get('blocked', 0)}\n")
        text_parts.append(f"- 成功率: {data.get('success_rate', 0)}%\n")
    else:
        text_parts.append("*该轮次无可用报告*")

    images: list[str] = []
    cases_dir = RESULTS_ROOT / round_dir / "cases"
    if cases_dir.exists():
        for case_dir in sorted(cases_dir.iterdir()):
            if case_dir.is_dir():
                final_png = case_dir / "final.png"
                if final_png.exists():
                    images.append(str(final_png))

    return "\n".join(text_parts), images


def main() -> None:
    app = _build_app()
    app.queue(default_concurrency_limit=3, max_size=10)
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        css=APP_CSS,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
