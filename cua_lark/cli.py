from __future__ import annotations

import argparse
from pathlib import Path

from cua_lark.adapters.gui import DryRunGui, PyAutoGui
from cua_lark.adapters.screen import PyAutoGuiScreen, StaticScreen
from cua_lark.adapters.vlm import EchoVisionModel, build_vlm
from cua_lark.reporting.writer import write_run
from cua_lark.runtime.config import load_settings
from cua_lark.testing.cases import load_cases
from cua_lark.testing.run_context import create_run
from cua_lark.testing.runner import CaseRunner
from cua_lark.testing.rules import (
    DEFAULT_DOCS_RULE_NAMES,
    DEFAULT_IM_RULE_NAMES,
    default_rules_root,
    load_rule_bundle,
    render_rules_prompt,
    rule_hashes,
    rule_names,
    rule_paths,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run compact CUA-Lark GUI tests.")
    parser.add_argument("--cases", help="YAML test case file")
    parser.add_argument("--case", action="append", help="Run selected case id")
    parser.add_argument("--stage", action="append", help="Run selected test_stage")
    parser.add_argument("--scenario", help="Scenario prompt file (legacy, prefer --system-prompt)")
    parser.add_argument("--system-prompt", help="System prompt file (default: scenarios/system.md)")
    parser.add_argument("--round", default="round", help="Current test round name")
    parser.add_argument("--suite", default="cua-lark", help="Suite name shown in reports")
    parser.add_argument("--results-root", help="Directory containing all run rounds")
    parser.add_argument(
        "--rules",
        help="Comma-separated rule modules to load. Use 'auto' to choose Docs or IM starter rules from selected cases.",
    )
    parser.add_argument(
        "--rule-selection",
        choices=["static", "vlm"],
        default="vlm",
        help="Use static starter rules or ask the VLM to select rule modules from the current screenshot.",
    )
    parser.add_argument(
        "--no-default-rules",
        action="store_true",
        help="Disable the default starter rule modules.",
    )
    parser.add_argument(
        "--bare-user-prompt",
        action="store_true",
        help="Send only task/history in the execution user prompt; rely on the system prompt for schema and generic behavior.",
    )
    parser.add_argument(
        "--enable-docs-batch",
        action="store_true",
        help="Allow Docs cases to emit Action: batch() for controlled speed experiments.",
    )
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip per-case setup_instruction execution and start each case from the current live GUI state.",
    )
    parser.add_argument(
        "--no-activate-feishu-host",
        action="store_true",
        help="Disable the default lightweight Feishu desktop app activation before Feishu product cases.",
    )
    parser.add_argument(
        "--grounding-check",
        action="store_true",
        help="Ask the VLM to verify/correct risky click coordinates on an annotated screenshot before execution.",
    )
    parser.add_argument(
        "--grounding-check-mode",
        choices=["high-risk", "all"],
        default="high-risk",
        help="Use high-risk to check only dense/uncertain clicks, or all to check every click.",
    )
    parser.add_argument("--backend", help="VLM backend override")
    parser.add_argument("--config", help="Config YAML path")
    parser.add_argument(
        "--hybrid-locator",
        action="store_true",
        help="Use Accessibility candidates to refine high-confidence click points and skip VLM grounding checks when matched.",
    )
    parser.add_argument(
        "--capture",
        choices=["app", "full"],
        default="app",
        help="Screenshot source for live runs. app captures the largest Feishu/Lark window when available.",
    )
    parser.add_argument(
        "--prefer-browser-docs",
        action="store_true",
        help="When a Feishu Docs browser window is visible, capture that browser app window before the Feishu desktop window.",
    )
    parser.add_argument(
        "--allow-fullscreen-fallback",
        action="store_true",
        help="Allow live runs to fall back to full-screen capture when no matching app window is found.",
    )
    parser.add_argument(
        "--require-app-window",
        action="store_true",
        help="Fail capture instead of falling back to full-screen when no matching Feishu/Docs host window is found.",
    )
    parser.add_argument("--dry-run-response", help="Use a fixed model response and do not operate the GUI")
    parser.add_argument("--static-screen", help="Use a static screenshot instead of live capture")
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    cases_path = Path(args.cases) if args.cases else settings.default_cases
    system_path = Path(args.system_prompt) if args.system_prompt else settings.default_system_prompt
    results_root = Path(args.results_root) if args.results_root else settings.results_root

    cases = load_cases(cases_path, args.case, args.stage)
    if not cases:
        raise SystemExit("No cases selected.")

    system_prompt = system_path.read_text(encoding="utf-8") if system_path.exists() else ""
    scenarios_dir = settings.new_root / "cua_lark" / "scenarios"
    scenario_prompts: dict[str, str] = {}
    for name, filename in [("docs", "docs.md"), ("im", "im.md"), ("general", "general.md")]:
        path = scenarios_dir / filename
        if path.exists():
            scenario_prompts[name] = path.read_text(encoding="utf-8")
    rules_root = default_rules_root(settings.new_root)
    requested_rules: list[str] = [] if args.no_default_rules else _rule_names_for_args(args.rules, cases)
    if args.rules and args.rules.strip().lower() != "auto":
        requested_rules = [item.strip() for item in args.rules.split(",") if item.strip()]
    rule_modules = load_rule_bundle(requested_rules, rules_root)
    rules_prompt = render_rules_prompt(rule_modules)
    selected_rule_names = rule_names(rule_modules)
    selected_rule_paths = rule_paths(rule_modules, relative_to=settings.new_root)
    selected_rule_hashes = rule_hashes(rule_modules)
    rule_index_prompt = (rules_root / "index.md").read_text(encoding="utf-8") if (rules_root / "index.md").exists() else ""
    run = create_run(results_root, args.suite, args.round)
    app_names = list((settings.screenshot.get("app_names") or []) or ["飞书", "Feishu", "Lark"])
    browser_app_names = list((settings.screenshot.get("browser_app_names") or []) or ["Safari", "Google Chrome", "Chrome", "Arc"])
    browser_title_keywords = list(
        (settings.screenshot.get("browser_title_keywords") or []) or ["feishu.cn", "larksuite.com", "飞书云文档", "未命名文档"]
    )
    app_recovery_names = list(
        (settings.screenshot.get("app_recovery_names") or []) or ["飞书", "Feishu", "Lark", "Safari", "Google Chrome"]
    )
    # Auto-enable prefer_browser_docs when any selected case is a Docs product.
    prefer_browser_docs = args.prefer_browser_docs
    if not prefer_browser_docs and any((c.product or "").lower() == "docs" for c in cases):
        prefer_browser_docs = True

    screen = (
        StaticScreen(Path(args.static_screen))
        if args.static_screen
        else PyAutoGuiScreen(
            prefer_app_window=args.capture == "app",
            app_names=app_names,
            browser_app_names=browser_app_names,
            browser_title_keywords=browser_title_keywords,
            prefer_browser_docs=prefer_browser_docs,
            require_app_window=args.require_app_window or (prefer_browser_docs and not args.allow_fullscreen_fallback),
            app_recovery_names=app_recovery_names,
            recovery_attempts=int(settings.screenshot.get("recovery_attempts") or 2),
        )
    )
    gui = DryRunGui() if args.dry_run_response else PyAutoGui(settings)
    vlm = EchoVisionModel(args.dry_run_response) if args.dry_run_response else build_vlm(settings, args.backend)
    runner = CaseRunner(
        screen=screen,
        gui=gui,
        vlm=vlm,
        system_prompt=system_prompt,
        scenario_prompts=scenario_prompts,
        rules_prompt=rules_prompt,
        selected_rules=selected_rule_names,
        selected_rule_paths=selected_rule_paths,
        selected_rule_hashes=selected_rule_hashes,
        rule_selection_mode=args.rule_selection,
        rule_index_prompt=rule_index_prompt,
        rules_root=rules_root,
        new_root=settings.new_root,
        max_steps=args.max_steps,
        final_verify=False,
        grounding_check=args.grounding_check,
        grounding_check_mode=args.grounding_check_mode,
        hybrid_locator=args.hybrid_locator,
        app_names=app_names,
        bare_user_prompt=args.bare_user_prompt,
        backend_name=args.backend or "",
        vlm_call_options=dict(settings.vlm.get("call_profiles") or {}),
        skip_setup=args.skip_setup,
        activate_feishu_host=not args.no_activate_feishu_host and not args.static_screen and not args.dry_run_response,
    )

    results = []
    for case in cases:
        result = runner.run(case, run.cases_dir)
        results.append(result)
        write_run(run, results)
        print(f"{case.id}: {result.status.value} ({result.duration_seconds:.2f}s)")

    write_run(run, results)
    print(f"Report: {run.root / 'README.md'}")
    return 0 if all(item.passed for item in results) else 1


def _rule_names_for_args(value: str | None, cases) -> list[str]:
    if value and value.strip().lower() != "auto":
        return [item.strip() for item in value.split(",") if item.strip()]
    has_docs = any((case.product or "").lower() == "docs" for case in cases)
    if has_docs:
        names = list(DEFAULT_DOCS_RULE_NAMES)
        text = " ".join(" ".join([case.instruction, case.name, case.stage]).lower() for case in cases)
        if any(term in text for term in ["标题", "列表", "表格", "清单", "引用", "代码", "heading", "list", "table", "checklist"]):
            names.append("docs_structure")
        if any(term in text for term in ["链接", "加粗", "高亮", "格式", "link", "url", "bold", "highlight", "format"]):
            names.append("docs_format_link")
        if any(
            term in text
            for term in [
                "指定文本",
                "局部文本",
                "局部短语",
                "短句",
                "词语",
                "删除",
                "替换",
                "复制",
                "移动",
                "评论",
                "exact text",
                "target text",
                "partial phrase",
                "replace",
                "delete",
                "copy",
                "move",
                "comment",
            ]
        ):
            names.append("docs_exact_span")
        if any(term in text for term in ["分享", "权限", "协作者", "share", "permission", "collaborator"]):
            names.append("docs_share_permission")
        if any(term in text for term in ["本地", "markdown", "素材", "snippet", "片段", "议程"]):
            names.append("docs_local_material")
        return _dedupe(names)
    return list(DEFAULT_IM_RULE_NAMES)


def _enable_docs_batch(cases) -> None:
    for case in cases:
        if (case.product or "").lower() != "docs":
            continue
        normalized = {item.strip().lower() for item in case.allowed_actions}
        if "batch" not in normalized:
            case.allowed_actions.append("batch")
        explicit_normalized = {item.strip().lower() for item in case.explicit_allowed_actions}
        if "batch" not in explicit_normalized:
            case.explicit_allowed_actions.append("batch")
        if case.action_policy_source == "explicit":
            case.action_policy_source = "merged"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
