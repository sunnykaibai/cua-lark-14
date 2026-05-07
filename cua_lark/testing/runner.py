from __future__ import annotations

import platform
import re
import subprocess
import time
from pathlib import Path
from PIL import Image

from datetime import datetime as dt_datetime

from cua_lark.adapters.gui import Gui
from cua_lark.adapters.screen import (
    Screen,
    capture_metadata,
    save_elements_overlay,
    save_grounding_crop,
    save_png,
    visual_change,
)
from cua_lark.adapters.vlm import VisionModel
from cua_lark.domain.action_parser import parse_action
from cua_lark.domain.models import Action, ActionKind, CaseResult, Status, StepResult, TestCase
from cua_lark.testing.grounding_check import (
    apply_grounding_check_response,
    build_grounding_check,
    grounding_check_risk,
    needs_grounding_check,
)
from cua_lark.testing.hybrid_locator import apply_hybrid_locator
from cua_lark.testing.lark_cli_verify import format_cli_verifier_response, verify_im_message_with_lark_cli
from cua_lark.testing.observation import interpret_visual_change
from cua_lark.reporting.writer import write_case
from cua_lark.testing.setup import build_setup_step_prompt
from cua_lark.testing.prompt import build_step_prompt
from cua_lark.testing.process_quality import evaluate_process_quality
from cua_lark.testing.rule_selector import (
    RULE_SELECTION_SYSTEM_PROMPT,
    RuleSelection,
    build_rule_selection_prompt,
    parse_rule_selection,
)
from cua_lark.testing.rules import load_rule_bundle, render_rules_prompt, rule_hashes, rule_paths
from cua_lark.testing.run_context import case_dir_name


class CaseRunner:
    def __init__(
        self,
        *,
        screen: Screen,
        gui: Gui,
        vlm: VisionModel,
        system_prompt: str = "",
        scenario_prompt: str = "",
        scenario_prompts: dict[str, str] | None = None,
        rules_prompt: str = "",
        selected_rules: list[str] | None = None,
        selected_rule_paths: list[str] | None = None,
        selected_rule_hashes: dict[str, str] | None = None,
        rule_selection_mode: str = "static",
        rule_index_prompt: str = "",
        rules_root: Path | None = None,
        new_root: Path | None = None,
        max_steps: int = 12,
        final_verify: bool = False,
        grounding_check: bool = False,
        grounding_check_mode: str = "high-risk",
        hybrid_locator: bool = False,
        app_names: list[str] | None = None,
        bare_user_prompt: bool = False,
        backend_name: str = "",
        vlm_call_options: dict[str, dict[str, object]] | None = None,
        skip_setup: bool = False,
        activate_feishu_host: bool = True,
        cancel_event: object = None,
    ) -> None:
        self.screen = screen
        self.gui = gui
        self.vlm = vlm
        self.system_prompt = system_prompt or scenario_prompt
        self.scenario_prompt = system_prompt or scenario_prompt
        self.scenario_prompts = scenario_prompts or {}
        self.rules_prompt = rules_prompt
        self.selected_rules = list(selected_rules or [])
        self.selected_rule_paths = list(selected_rule_paths or [])
        self.selected_rule_hashes = dict(selected_rule_hashes or {})
        self.rule_selection_mode = rule_selection_mode
        self.rule_index_prompt = rule_index_prompt
        self.rules_root = rules_root
        self.new_root = new_root
        self.max_steps = max_steps
        self.final_verify = final_verify
        self.grounding_check = grounding_check
        self.grounding_check_mode = grounding_check_mode
        self.hybrid_locator = hybrid_locator
        self.app_names = list(app_names or [])
        self.bare_user_prompt = bare_user_prompt
        self.backend_name = backend_name
        self.vlm_call_options = dict(vlm_call_options or {})
        self.skip_setup = skip_setup
        self.activate_feishu_host = activate_feishu_host
        self.cancel_event = cancel_event

    def _is_cancelled(self) -> bool:
        ev = self.cancel_event
        return ev is not None and getattr(ev, "is_set", lambda: False)()

    def _system_prompt_for_case(self, case: TestCase) -> str:
        product = (case.product or "").lower()
        if product in self.scenario_prompts:
            return self.scenario_prompts[product]
        return self.system_prompt

    def _complete_vlm(self, image, prompt: str, *, system_prompt: str = "", profile: str = "execution") -> str:
        options = dict(self.vlm_call_options.get(profile, {}))
        return self.vlm.complete(image, prompt, system_prompt=system_prompt, options=options or None)

    def run(self, case: TestCase, cases_root: Path) -> CaseResult:
        reset_capture_state = getattr(self.screen, "reset_transient_capture_state", None)
        if callable(reset_capture_state):
            reset_capture_state()
        if self.activate_feishu_host:
            _activate_feishu_host_for_case(case)
        case_dir = cases_root / case_dir_name(case.id, case.name)
        case_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        started_at = dt_datetime.now().astimezone()
        started_at_text = started_at.isoformat(timespec="seconds")
        result = CaseResult(case=case, status=Status.RUNNING, started_at=started_at_text)
        prepare_started = time.time()
        result.screen_preparation = _prepare_screen_for_case(self.screen)
        result.screen_preparation["seconds"] = round(time.time() - prepare_started, 3)
        if case.setup_instruction.strip() and not self.skip_setup:
            setup_result = self._run_setup(case, case_dir)
            result.setup_steps = setup_result.steps
            if setup_result.status != Status.PASSED:
                result.status = Status.BLOCKED
                result.failure = f"setup failed: {setup_result.failure or setup_result.status.value}"
                result.duration_seconds = round(time.time() - started, 2)
                try:
                    final_image = self.screen.capture()
                except Exception:
                    final_image = Image.new("RGB", (1000, 700), "white")
                result.final_screenshot = save_png(final_image, case_dir / "final.png")
                write_case(case_dir, result)
                return result
        terminal_image = None
        fallback_image = Image.new("RGB", (1000, 700), "white")
        case_rule_selection: RuleSelection | None = None
        case_goal_contract = None
        case_rules_prompt = self.rules_prompt
        case_rule_paths = self.selected_rule_paths
        case_rule_hashes = self.selected_rule_hashes
        case_selected_rules = self.selected_rules

        for index in range(1, self.max_steps + 1):
            if self._is_cancelled():
                result.status = Status.FAILED
                result.failure = "user cancelled"
                break
            step_started = time.time()
            capture_started = time.time()
            try:
                before_image = self.screen.capture()
                fallback_image = before_image
            except Exception as exc:
                before_image = fallback_image
                before_name = save_png(before_image, case_dir / f"{index:02d}-before.png")
                after_name = save_png(before_image, case_dir / f"{index:02d}-after.png")
                step = StepResult(
                    index=index,
                    action=None,
                    before=before_name,
                    after=after_name,
                    passed=False,
                    message=str(exc),
                    visual_change={"status": "capture-failed"},
                    screenshot={},
                    timing={"total_step_seconds": round(time.time() - step_started, 3)},
                )
                result.steps.append(step)
                result.status = Status.FAILED
                result.failure = str(exc)
                write_case(case_dir, result)
                break
            capture_before_seconds = time.time() - capture_started
            before_name = save_png(before_image, case_dir / f"{index:02d}-before.png")
            raw = ""
            grounding_check_image = ""
            selection = RuleSelection(selected_rules=case_selected_rules)
            current_rules_prompt = case_rules_prompt
            current_rule_paths = case_rule_paths
            current_rule_hashes = case_rule_hashes
            current_selected_rules = case_selected_rules
            rule_selection_started = time.time()
            if self.rule_selection_mode == "vlm":
                if case_rule_selection is None:
                    case_rule_selection = self._select_rules(case, result.steps, before_image)
                    case_goal_contract = case_rule_selection.goal_contract
                    case_goal_contract.metadata = case_rule_selection.metadata
                    result.goal_contract = case_goal_contract
                    case_selected_rules = case_rule_selection.selected_rules
                    if self.rules_root:
                        modules = load_rule_bundle(case_selected_rules, self.rules_root)
                        case_rules_prompt = render_rules_prompt(modules)
                        case_rule_paths = rule_paths(modules, relative_to=self.new_root)
                        case_rule_hashes = rule_hashes(modules)
                    selection = case_rule_selection
                else:
                    selection = RuleSelection(
                        selected_rules=case_selected_rules,
                        goal_contract=case_goal_contract,
                        reason=f"reused initial case rule selection from step 1: {case_rule_selection.reason}",
                    )
                current_selected_rules = case_selected_rules
                current_rules_prompt = case_rules_prompt
                current_rule_paths = case_rule_paths
                current_rule_hashes = case_rule_hashes
            rule_selection_seconds = time.time() - rule_selection_started
            if case.stage.endswith("_setup"):
                step_prompt = build_setup_step_prompt(
                    case,
                    result.steps,
                    rules_prompt="" if self.bare_user_prompt else current_rules_prompt,
                    goal_contract=case_goal_contract,
                )
            else:
                step_prompt = build_step_prompt(
                    case,
                    result.steps,
                    rules_prompt="" if self.bare_user_prompt else current_rules_prompt,
                    goal_contract=case_goal_contract,
                    case_started_at=started_at_text,
                    current_time=dt_datetime.now().astimezone().isoformat(timespec="seconds"),
                )
            grounding_check_prompt = ""
            action = None
            passed = False
            message = ""
            timing: dict[str, float | int] = {
                "capture_before_seconds": round(capture_before_seconds, 3),
                "rule_selection_seconds": round(rule_selection_seconds, 3),
                "main_vlm_seconds": 0.0,
                "parse_seconds": 0.0,
                "grounding_check_seconds": 0.0,
                "grounding_check_vlm_seconds": 0.0,
                "grounding_check_calls": 0,
                "execute_seconds": 0.0,
                "capture_after_seconds": 0.0,
                "report_seconds": 0.0,
                "hybrid_locator_seconds": 0.0,
                "hybrid_locator_hits": 0,
            }
            try:
                metadata = capture_metadata(before_image)
                vlm_started = time.time()
                raw = self._complete_vlm(
                    before_image,
                    step_prompt,
                    system_prompt=self._system_prompt_for_case(case),
                    profile="execution",
                )
                vlm_metadata = _vlm_metadata(self.vlm)
                timing["main_vlm_seconds"] = round(time.time() - vlm_started, 3)
                parse_started = time.time()
                action = parse_action(raw, before_image.size, metadata)
                timing["parse_seconds"] = round(time.time() - parse_started, 3)
                _expand_input_material_reference(action, case)
                action = _suppress_repeated_docs_bold_toggle(case, action, result.steps)
                action = _suppress_repeated_docs_structure_insertion_click(case, action, result.steps)
                action = _suppress_docs_structure_slash_before_find_closed(case, action, result.steps)
                action = _suppress_docs_global_create_menu_for_structure(case, action)
                action = _convert_docs_structure_slash_text_to_keypress(case, action)
                action = _split_docs_divider_focus_from_shortcut_batch(case, action)
                action = _suppress_docs_divider_menu_loop(case, action, result.steps)
                action = _suppress_repeated_docs_divider_shortcut(case, action, result.steps)
                action = _suppress_early_docs_table_repair_finish(case, action, result.steps)
                if action.is_terminal:
                    passed = True
                    message = action.text or "model finished"
                    after_image = before_image
                elif _suppress_browser_precheck_action(self.screen, case, action, metadata):
                    action = Action(
                        kind=ActionKind.WAIT,
                        target="app-first recovery after browser precheck",
                        thought="Browser Docs precheck did not finish on the exact target; skip browser navigation and recover the Feishu app entry route.",
                        raw_text=raw,
                    )
                    capture_after_started = time.time()
                    after_image = _capture_with_retries(self.screen)
                    timing["capture_after_seconds"] = round(time.time() - capture_after_started, 3)
                    fallback_image = after_image
                    passed = True
                    message = "browser precheck suppressed; recovered app-first"
                else:
                    _guard_unsafe_gui_action(case, action, metadata, step_index=index)
                    self._execute_action(action, before_image, case, case_dir, index, metadata, timing)
                    _arm_browser_handoff_after_open_action(self.screen, case, action)
                    grounding_check_image = _first_grounding_check_field(action, "image")
                    grounding_check_prompt = _first_grounding_check_field(action, "prompt")
                    capture_after_started = time.time()
                    after_image = _capture_with_retries(self.screen)
                    timing["capture_after_seconds"] = round(time.time() - capture_after_started, 3)
                    fallback_image = after_image
                    passed = True
                    message = "executed"
            except Exception as exc:
                try:
                    capture_after_started = time.time()
                    after_image = self.screen.capture()
                    timing["capture_after_seconds"] = round(time.time() - capture_after_started, 3)
                    fallback_image = after_image
                except Exception:
                    after_image = before_image
                message = str(exc)

            report_started = time.time()
            after_name = save_png(after_image, case_dir / f"{index:02d}-after.png")
            grounding_crop = ""
            elements_overlay = ""
            if action and action.grounding:
                grounding_crop = save_grounding_crop(
                    before_image,
                    action.grounding,
                    case_dir / f"{index:02d}-grounding.png",
                )
                elements = action.grounding.get("elements")
                if isinstance(elements, list):
                    elements_overlay = save_elements_overlay(
                        before_image,
                        elements,
                        case_dir / f"{index:02d}-elements.png",
                    )
            step = StepResult(
                index=index,
                action=action,
                before=before_name,
                after=after_name,
                grounding_crop=grounding_crop,
                elements_overlay=elements_overlay,
                grounding_check_image=grounding_check_image,
                system_prompt=self._system_prompt_for_case(case) if not result.steps else "",
                prompt=step_prompt,
                rules_prompt=current_rules_prompt,
                rule_selection_prompt=selection.prompt,
                rule_selection_raw=selection.raw,
                rule_selection_reasoning=selection.reasoning,
                rule_selection_metadata=selection.metadata,
                rule_selection_reason=selection.reason,
                rule_selection_fallback_used=selection.fallback_used,
                rule_selection_error=selection.error,
                selected_rules=current_selected_rules,
                selected_rule_paths=current_rule_paths,
                selected_rule_hashes=current_rule_hashes,
                grounding_check_prompt=grounding_check_prompt,
                passed=passed,
                message=message,
                visual_change=interpret_visual_change(action, visual_change(before_image, after_image)),
                screenshot=capture_metadata(before_image),
                raw_model=raw,
                reasoning=str(vlm_metadata.get("reasoning_content") or ""),
                vlm_metadata=vlm_metadata,
                timing={**timing, "total_step_seconds": round(time.time() - step_started, 3)},
            )
            result.steps.append(step)
            step.timing["report_seconds"] = round(time.time() - report_started, 3)
            step.timing["total_step_seconds"] = round(time.time() - step_started, 3)
            write_case(case_dir, result)
            if not passed:
                result.status = Status.FAILED
                result.failure = message
                break
            if action and action.is_terminal:
                terminal_image = after_image
                result.status = Status.PASSED
                break
        else:
            result.status = Status.FAILED
            result.failure = f"max steps reached: {self.max_steps}"

        if terminal_image is not None:
            final_image = terminal_image
        else:
            try:
                final_image = self.screen.capture()
                fallback_image = final_image
            except Exception:
                final_image = fallback_image
        if final_image is None:
            final_image = fallback_image
        result.final_screenshot = save_png(final_image, case_dir / "final.png")
        cli_result = verify_im_message_with_lark_cli(case, started_at, dt_datetime.now().astimezone())
        result.cli_verifier_response = format_cli_verifier_response(cli_result)
        result.cli_verifier_metadata = cli_result
        result.duration_seconds = round(time.time() - started, 2)
        result.finished_at = dt_datetime.now().astimezone().isoformat(timespec="seconds")
        result.process_quality = evaluate_process_quality(result)
        blocking = result.process_quality.get("blocking_warnings") or []
        if result.status == Status.PASSED and blocking:
            result.status = Status.FAILED
            result.failure = f"blocking process quality warnings: {', '.join(blocking)}"
        write_case(case_dir, result)
        return result

    def _run_setup(self, case: TestCase, case_dir: Path) -> CaseResult:
        setup_case = TestCase(
            id=f"{case.id}-SETUP",
            name=f"{case.name} setup",
            instruction=case.setup_instruction,
            expected=case.setup_expected or "起始背景已经准备好",
            product=case.product,
            phase=case.phase,
            stage=f"{case.stage}_setup",
            verification={"method": "model_finished", "assertion": case.setup_expected or "起始背景已经准备好"},
            allowed_actions=list(case.allowed_actions),
            input_materials=list(case.input_materials),
        )
        setup_runner = CaseRunner(
            screen=self.screen,
            gui=self.gui,
            vlm=self.vlm,
            scenario_prompt=self.scenario_prompt,
            scenario_prompts=self.scenario_prompts,
            rules_prompt=self.rules_prompt,
            selected_rules=self.selected_rules,
            selected_rule_paths=self.selected_rule_paths,
            selected_rule_hashes=self.selected_rule_hashes,
            rule_selection_mode=self.rule_selection_mode,
            rule_index_prompt=self.rule_index_prompt,
            rules_root=self.rules_root,
            new_root=self.new_root,
            max_steps=case.setup_max_steps,
            final_verify=False,
            grounding_check=self.grounding_check,
            grounding_check_mode=self.grounding_check_mode,
            backend_name=self.backend_name,
            skip_setup=False,
        )
        old_require_app_window = getattr(self.screen, "require_app_window", None)
        if old_require_app_window is not None:
            setattr(self.screen, "require_app_window", False)
        try:
            return setup_runner.run(setup_case, case_dir / "setup")
        finally:
            if old_require_app_window is not None:
                setattr(self.screen, "require_app_window", old_require_app_window)

    def _select_rules(self, case: TestCase, history: list[StepResult], before_image) -> RuleSelection:
        fallback = self.selected_rules
        if not (self.rule_index_prompt and self.rules_root):
            return RuleSelection(
                selected_rules=fallback,
                fallback_used=True,
                error="rule selector not configured",
            )
        prompt = build_rule_selection_prompt(case, history, self.rule_index_prompt)
        try:
            raw = self._complete_vlm(
                before_image, prompt,
                system_prompt=RULE_SELECTION_SYSTEM_PROMPT,
                profile="rule_selection",
            )
            metadata = _vlm_metadata(self.vlm)
            selection = parse_rule_selection(raw, _available_rule_names(self.rules_root), fallback)
            selection.selected_rules = _ensure_required_rule_modules(case, selection.selected_rules)
            selection.prompt = prompt
            selection.reasoning = str(metadata.get("reasoning_content") or "")
            selection.metadata = metadata
            return selection
        except Exception as exc:
            return RuleSelection(
                selected_rules=_ensure_required_rule_modules(case, fallback),
                prompt=prompt,
                fallback_used=True,
                error=str(exc),
            )

    def _execute_action(
        self,
        action: Action,
        before_image,
        case: TestCase,
        case_dir: Path,
        step_index: int,
        metadata: dict[str, object],
        timing: dict[str, float | int],
    ) -> None:
        if action.kind == ActionKind.BATCH:
            _ensure_action_allowed(action, case)
            if not action.sub_actions:
                raise ValueError("Batch action has no sub-actions")
            for sub_index, sub_action in enumerate(action.sub_actions, start=1):
                _ensure_action_allowed(sub_action, case, context="Batch sub-action")
                _expand_input_material_reference(sub_action, case)
                if self.hybrid_locator:
                    locator_start = time.time()
                    locator_result = apply_hybrid_locator(sub_action, app_names=list(self.app_names), metadata={})
                    timing["hybrid_locator_seconds"] = round(float(timing.get("hybrid_locator_seconds", 0)) + time.time() - locator_start, 3)
                    if locator_result.matched:
                        timing["hybrid_locator_hits"] = int(timing.get("hybrid_locator_hits", 0)) + 1
                    if not locator_result.matched:
                        self._maybe_grounding_check(
                            sub_action, before_image, case, case_dir,
                            f"{step_index:02d}-grounding-check-{sub_index}.png",
                            metadata, timing,
                        )
                else:
                    self._maybe_grounding_check(
                        sub_action, before_image, case, case_dir,
                        f"{step_index:02d}-grounding-check-{sub_index}.png",
                        metadata, timing,
                    )
                execute_started = time.time()
                _activate_captured_app_for_docs(case, metadata)
                _ensure_target_app_front(self.screen, case, metadata)
                if not self._is_cancelled():
                    self.gui.execute(sub_action)
                _arm_browser_handoff_after_open_action(self.screen, case, sub_action)
                timing["execute_seconds"] = round(float(timing["execute_seconds"]) + time.time() - execute_started, 3)
            action.grounding_check["batch_sub_actions"] = [
                {
                    "index": index,
                    "action": sub_action.kind.value,
                    "target": sub_action.target,
                    "grounding_check": sub_action.grounding_check,
                }
                for index, sub_action in enumerate(action.sub_actions, start=1)
            ]
            return

        _ensure_action_allowed(action, case)
        if self.hybrid_locator:
            locator_start = time.time()
            locator_result = apply_hybrid_locator(action, app_names=list(self.app_names), metadata={})
            timing["hybrid_locator_seconds"] = round(float(timing.get("hybrid_locator_seconds", 0)) + time.time() - locator_start, 3)
            if locator_result.matched:
                timing["hybrid_locator_hits"] = int(timing.get("hybrid_locator_hits", 0)) + 1
            if not locator_result.matched:
                self._maybe_grounding_check(
                    action, before_image, case, case_dir,
                    f"{step_index:02d}-grounding-check.png",
                    metadata, timing,
                )
        else:
            self._maybe_grounding_check(
                action,
                before_image,
                case,
                case_dir,
                f"{step_index:02d}-grounding-check.png",
                metadata,
                timing,
            )
        execute_started = time.time()
        _activate_captured_app_for_docs(case, metadata)
        _ensure_target_app_front(self.screen, case, metadata)
        if not self._is_cancelled():
            self.gui.execute(action)
        timing["execute_seconds"] = round(float(timing["execute_seconds"]) + time.time() - execute_started, 3)

    def _maybe_grounding_check(
        self,
        action: Action,
        before_image,
        case: TestCase,
        case_dir: Path,
        filename: str,
        metadata: dict[str, object],
        timing: dict[str, float | int],
    ) -> str:
        check_started = time.time()
        if not (self.grounding_check and needs_grounding_check(action)):
            timing["grounding_check_seconds"] = round(float(timing["grounding_check_seconds"]) + time.time() - check_started, 3)
            return ""
        risk = grounding_check_risk(action, mode=self.grounding_check_mode)
        if not risk["triggered"]:
            action.grounding_check = risk
            timing["grounding_check_seconds"] = round(float(timing["grounding_check_seconds"]) + time.time() - check_started, 3)
            return ""
        check = build_grounding_check(action, before_image, case)
        image_name = save_png(check.annotated_image, case_dir / filename)
        check_raw = self._complete_vlm(
            check.annotated_image, check.prompt,
            profile="grounding_check",
        )
        apply_grounding_check_response(action, check_raw, before_image.size, metadata)
        action.grounding_check.update(risk)
        action.grounding_check["image"] = image_name
        action.grounding_check["prompt"] = check.prompt
        timing["grounding_check_calls"] = int(timing["grounding_check_calls"]) + 1
        timing["grounding_check_seconds"] = round(float(timing["grounding_check_seconds"]) + time.time() - check_started, 3)
        return image_name


def _expand_input_material_reference(action: Action | None, case: TestCase) -> None:
    if not action or action.kind != ActionKind.TYPE_TEXT or not action.text:
        return
    reference = action.text.strip()
    if not (reference.startswith("{material:") and reference.endswith("}")):
        return
    label = reference.removeprefix("{material:").removesuffix("}")
    for material in case.input_materials:
        if material.get("label") == label:
            action.text = material.get("content") or ""
            return


def _arm_browser_handoff_after_open_action(screen: Screen, case: TestCase, action: Action | None) -> None:
    if not action or (case.product or "").lower() != "docs":
        return
    if action.kind not in {ActionKind.CLICK, ActionKind.DOUBLE_CLICK, ActionKind.HOTKEY}:
        return
    text = " ".join([case.instruction, case.name, case.stage, action.target, action.thought, action.raw_text]).lower()
    if not _contains_any(text, ["打开", "切换", "open", "entry", "入口", "搜索结果", "search result", "document result"]):
        return
    if not _contains_any(text, ["文档", "docs", "document", "cloud docs", "云文档"]):
        return
    if action.kind == ActionKind.HOTKEY and (action.key or "").lower() != "enter":
        return
    arm = getattr(screen, "arm_browser_handoff", None)
    if callable(arm):
        arm(4)


def _suppress_browser_precheck_action(screen: Screen, case: TestCase, action: Action | None, metadata: dict[str, object]) -> bool:
    if not action or action.is_terminal:
        return False
    if (case.product or "").lower() != "docs":
        return False
    if metadata.get("capture_role") != "browser_precheck":
        return False
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not _is_docs_entry_case(case, text) and not _is_docs_target_document_case(case, text):
        return False
    if _is_docs_target_document_case(case, text) and not _is_browser_precheck_navigation_action(action):
        return False
    suppress = getattr(screen, "suppress_browser_precheck", None)
    if callable(suppress):
        suppress()
    return True


def _is_docs_entry_case(case: TestCase, text: str | None = None) -> bool:
    if case.id.startswith("DOCS-ENTRY-"):
        return True
    lowered = text if text is not None else " ".join([case.instruction, case.name, case.stage]).lower()
    return _contains_any(lowered, ["入口", "entry", "docs_entry_robustness"]) and _contains_any(
        lowered,
        ["打开", "切换", "open", "文档", "document"],
    )


def _is_docs_target_document_case(case: TestCase, text: str | None = None) -> bool:
    if (case.product or "").lower() != "docs":
        return False
    lowered = text if text is not None else " ".join([case.instruction, case.name, case.stage]).lower()
    if "“" in " ".join([case.instruction, case.name]) or '"' in " ".join([case.instruction, case.name]):
        return True
    return _contains_any(
        lowered,
        [
            "provision",
            "clean",
            "打开",
            "新建",
            "创建",
            "目标文档",
            "target document",
            "document title",
        ],
    ) and _contains_any(lowered, ["文档", "docs", "document", "云文档"])


def _is_browser_precheck_navigation_action(action: Action) -> bool:
    if action.kind not in {ActionKind.CLICK, ActionKind.DOUBLE_CLICK, ActionKind.RIGHT_CLICK, ActionKind.HOTKEY}:
        return False
    text = " ".join([action.target, action.thought, action.raw_text, action.key]).lower()
    if _contains_any(
        text,
        [
            "browser",
            "浏览器",
            "tab",
            "new tab",
            "address bar",
            "url",
            "history",
            "docs home",
            "browser docs",
            "search",
            "搜索",
            "新建",
            "创建",
            "create",
            "home",
            "云文档",
        ],
    ):
        return True
    if action.kind == ActionKind.HOTKEY and (action.key or "").lower() in {"command l", "cmd l", "meta l"}:
        return True
    return False


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _activate_captured_app_for_docs(case: TestCase, metadata: dict[str, object]) -> None:
    if (case.product or "").lower() != "docs":
        return
    app_name = str(metadata.get("app_name") or "")
    app = _normal_macos_app_name(app_name)
    if not app or platform.system() != "Darwin":
        return
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{_escape_applescript(app)}" to activate'],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        time.sleep(0.15)
    except Exception:
        return


def _ensure_target_app_front(screen: Screen, case: TestCase, metadata: dict[str, object]) -> None:
    if platform.system() != "Darwin":
        return
    product = (case.product or "").lower()
    if product == "docs":
        app_name = str(metadata.get("app_name") or "")
        app = _normal_macos_app_name(app_name) or "Safari"
    else:
        app = "飞书"
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{_escape_applescript(app)}" to activate'],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        time.sleep(0.1)
    except Exception:
        return


def _activate_feishu_host_for_case(case: TestCase) -> bool:
    """Bring the Feishu desktop host forward for Feishu products before Seed acts.

    This is test-harness environment recovery only: it activates the host app and
    never navigates to a product module, searches, opens objects, or edits data.
    Docs keeps its browser-target precheck path because an already-open target
    browser document may itself be the correct starting surface.
    """
    if platform.system() != "Darwin" or not _needs_feishu_host_activation(case):
        return False
    for app in ("飞书", "Feishu", "Lark"):
        try:
            completed = subprocess.run(
                ["osascript", "-e", f'tell application "{_escape_applescript(app)}" to activate'],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
        except Exception:
            continue
        if completed.returncode == 0:
            time.sleep(0.35)
            return True
    return False


def _needs_feishu_host_activation(case: TestCase) -> bool:
    product = (case.product or "").strip().lower()
    if product == "docs":
        return False
    if product in {"im", "calendar", "mail", "base", "vc"}:
        return True
    text = " ".join([case.id, case.name, case.instruction, case.expected, case.stage]).lower()
    return any(
        token in text
        for token in [
            "飞书",
            "feishu",
            "lark",
            "日历",
            "calendar",
            "消息",
            "聊天",
            "im",
            "邮箱",
            "mail",
            "多维表格",
            "base",
            "视频会议",
            "vc",
        ]
    )


def _normal_macos_app_name(value: str) -> str:
    lowered = (value or "").lower()
    if "safari" in lowered:
        return "Safari"
    if "chrome" in lowered:
        return "Google Chrome"
    if "arc" in lowered:
        return "Arc"
    if "飞书" in value:
        return "飞书"
    if "feishu" in lowered:
        return "Feishu"
    if "lark" in lowered:
        return "Lark"
    return ""


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _ensure_required_rule_modules(case: TestCase, names: list[str]) -> list[str]:
    if (case.product or "").lower() != "docs":
        return list(names)
    required = ["live_object", "docs_shell"]
    result: list[str] = []
    for name in [*required, *names]:
        if name and name not in result:
            result.append(name)
    return result


def _guard_setup_action(case: TestCase, action: Action | None, metadata: dict[str, object]) -> None:
    _guard_unsafe_gui_action(case, action, metadata, step_index=0)


# Number of initial steps where navigation to Docs is allowed (grace period).
_DOCS_NAV_GRACE_STEPS = 3


def _guard_unsafe_gui_action(
    case: TestCase, action: Action | None, metadata: dict[str, object], *, step_index: int = 0
) -> None:
    if not action or (case.product or "").lower() != "docs":
        return
    # Grace period: allow first few steps for navigating TO the Docs area.
    if step_index < _DOCS_NAV_GRACE_STEPS:
        return
    if action.kind not in {ActionKind.CLICK, ActionKind.DOUBLE_CLICK, ActionKind.RIGHT_CLICK, ActionKind.HOTKEY}:
        return
    text = " ".join([action.target, action.thought, action.raw_text, action.key]).lower()
    if _mentions_browser_tab(text):
        if not _is_exact_target_document_browser_tab(case, action):
            raise ValueError(f"blocked unsafe Docs action outside Feishu/Docs content area: {action.target or action.kind.value}")
        return
    forbidden = [
        "macos",
        "menu bar",
        "菜单栏",
        "dock",
        "app switcher",
        "system menu",
        "window menu",
        "finder",
        "vs code",
        "visual studio code",
        "code editor",
        "编辑器",
        "chrome address",
        "browser chrome",
        "address bar",
        "red close",
        "红色关闭",
        "窗口关闭",
        "traffic light",
    ]
    if _contains_any(text, forbidden):
        raise ValueError(f"blocked unsafe Docs action outside Feishu/Docs content area: {action.target or action.kind.value}")
    capture_type = str(metadata.get("capture_type") or "")
    app_name = str(metadata.get("app_name") or "")
    if capture_type.startswith("full_screen") and action.kind in {
        ActionKind.CLICK,
        ActionKind.DOUBLE_CLICK,
        ActionKind.RIGHT_CLICK,
        ActionKind.HOTKEY,
    }:
        if not _is_feishu_docs_host_name(app_name):
            raise ValueError("blocked Docs action on full-screen capture without Feishu/Docs host evidence")


def _is_exact_target_document_browser_tab(case: TestCase, action: Action) -> bool:
    if action.kind not in {ActionKind.CLICK, ActionKind.DOUBLE_CLICK}:
        return False
    text = " ".join([action.target, action.thought, action.raw_text]).lower()
    if not _mentions_browser_tab(text):
        return False
    return any(title.lower() in text for title in _case_quoted_titles(case))


def _mentions_browser_tab(text: str) -> bool:
    lowered = text.lower()
    return _contains_any(lowered, ["browser tab", "浏览器标签", "标签页"]) or re.search(r"\btab\b", lowered) is not None


def _case_quoted_titles(case: TestCase) -> list[str]:
    raw = " ".join([case.instruction, case.name, case.expected])
    titles = re.findall(r"[“\"]([^”\"]{6,})[”\"]", raw)
    return [title.strip() for title in titles if title.strip()]


def _suppress_repeated_docs_bold_toggle(case: TestCase, action: Action | None, history: list[StepResult]) -> Action | None:
    if not action or not _is_docs_bold_format_case(case) or not _is_docs_bold_toggle_action(action):
        return action
    prior_toggles = [step.action for step in history if step.action and _is_docs_bold_toggle_action(step.action)]
    if not prior_toggles:
        return action
    if not any(_same_docs_bold_toggle_target(item, action) for item in prior_toggles):
        return action
    # A prior bold toggle already happened earlier in the case, even if the model
    # inserted drag / edit-mode / wait steps in between. Do not let it toggle bold
    # again on the same target because bold is a true toggle and may clear itself.
    return Action(
        kind=ActionKind.HOTKEY,
        key="esc",
        target=action.target,
        thought="Suppress repeated Docs bold toggle on the same target; clear transient selection/find state before final verification.",
        expected="Transient selection or find highlighting is dismissed without toggling bold back off.",
        raw_text=action.raw_text,
    )


def _suppress_repeated_docs_structure_insertion_click(
    case: TestCase, action: Action | None, history: list[StepResult]
) -> Action | None:
    if not action or action.kind != ActionKind.CLICK or not _is_docs_structure_after_find_case(case):
        return action
    if not _is_docs_structure_insertion_point_action(action):
        return action
    recent_clicks = [
        step.action
        for step in history[-3:]
        if step.action
        and step.action.kind == ActionKind.CLICK
        and _is_docs_structure_insertion_point_action(step.action)
    ]
    if not recent_clicks:
        return action
    return Action(
        kind=ActionKind.HOTKEY,
        key="enter",
        target="advance from prepared Docs structure insertion point",
        thought="Suppress repeated click on the same Docs anchor insertion point; create the empty body block so the next step can insert the requested structure.",
        expected="A new empty body block appears after the full anchor sentence, ready for table/divider insertion.",
        raw_text=action.raw_text,
    )


def _suppress_docs_structure_slash_before_find_closed(
    case: TestCase, action: Action | None, history: list[StepResult]
) -> Action | None:
    if not action or not _is_docs_structure_after_find_case(case) or not _is_slash_text_action(action):
        return action
    if any(_is_docs_structure_esc_action(step.action) for step in history[-8:]):
        return action
    saw_find = any(
        step.action
        and (
            (step.action.kind == ActionKind.HOTKEY and (step.action.key or "").lower() == "command f")
            or _contains_any(
                " ".join([step.action.target, step.action.thought, step.action.raw_text]).lower(),
                ["find", "查找", "搜索"],
            )
        )
        for step in history[-8:]
    )
    reason = "Close the active Docs find/search panel before using slash commands or inserting a table/divider structure."
    if not saw_find:
        reason = "Clear any active Docs find/search popup, selection toolbar, or stale slash-command state before the first slash command for a structure task."
    return Action(
        kind=ActionKind.HOTKEY,
        key="esc",
        target="open document find/search panel before structure insertion",
        thought=reason,
        expected="Transient popups/highlights close; the anchor remains visible so the next step can place the caret after the full sentence punctuation.",
        raw_text=action.raw_text,
    )


def _suppress_docs_global_create_menu_for_structure(case: TestCase, action: Action | None) -> Action | None:
    if not action or not _is_docs_structure_after_find_case(case):
        return action
    candidates = [action, *action.sub_actions] if action.kind == ActionKind.BATCH else [action]
    text = " ".join(
        " ".join([item.target, item.thought, item.raw_text, str(item.grounding.get("evidence") or "")])
        for item in candidates
    ).lower()
    if not _contains_any(text, ["top-right", "global", "new/create", "新建", "创建", "文档应用", "多维表格", "幻灯片", "问卷"]):
        return action
    if not _contains_any(text, ["+", "plus", "表格", "table", "insert"]):
        return action
    return Action(
        kind=ActionKind.HOTKEY,
        key="esc",
        target="top-right global create menu is not an inline Docs table insertion control",
        thought="Suppress global create/new menu path for an inline Docs structure task; close it and use a body-local table/divider control instead.",
        expected="The global create menu closes without creating a separate file or app object.",
        raw_text=action.raw_text,
    )


def _convert_docs_structure_slash_text_to_keypress(case: TestCase, action: Action | None) -> Action | None:
    if not action or not _is_docs_structure_after_find_case(case):
        return action
    if action.kind == ActionKind.TYPE_TEXT and action.text.strip() == "/":
        return Action(
            kind=ActionKind.HOTKEY,
            key="/",
            target=action.target,
            thought="Use a real slash keypress for the Docs slash command menu; pasted slash text may remain ordinary body text.",
            expected=action.expected or "A visible Docs slash command menu opens.",
            raw_text=action.raw_text,
        )
    if action.kind == ActionKind.BATCH:
        for sub_action in action.sub_actions:
            if sub_action.kind == ActionKind.TYPE_TEXT and sub_action.text.strip() == "/":
                sub_action.kind = ActionKind.HOTKEY
                sub_action.key = "/"
                sub_action.text = ""
                sub_action.thought = (
                    sub_action.thought
                    or "Use a real slash keypress for the Docs slash command menu; pasted slash text may remain ordinary body text."
                )
        return action
    return action


def _suppress_docs_divider_menu_loop(case: TestCase, action: Action | None, history: list[StepResult]) -> Action | None:
    if not action or not _is_docs_divider_case(case):
        return action
    if not _is_divider_menu_loop_action(action):
        return action
    menu_loop_count = sum(
        1
        for step in history[-8:]
        if step.action and _is_divider_menu_loop_action(step.action)
    )
    if menu_loop_count < 2:
        return action
    return Action(
        kind=ActionKind.HOTKEY,
        key="esc",
        target="divider insert menu loop fallback",
        thought=(
            "The divider task is looping inside an insert/slash menu without a visible divider option. "
            "Close the menu, then use the body Markdown divider shortcut `---` followed by Enter from the empty block."
        ),
        expected="The insert menu closes and the empty body block between the divider anchors remains available for the Markdown divider shortcut.",
        raw_text=action.raw_text,
    )


def _split_docs_divider_focus_from_shortcut_batch(case: TestCase, action: Action | None) -> Action | None:
    if not action or not _is_docs_divider_case(case) or action.kind != ActionKind.BATCH:
        return action
    if not _action_contains_divider_shortcut(action):
        return action
    first_click = next((item for item in action.sub_actions if item.kind == ActionKind.CLICK), None)
    if not first_click:
        return action
    return Action(
        kind=ActionKind.CLICK,
        point=first_click.point,
        target=first_click.target or action.target or "divider anchor focus point",
        thought=(
            "For divider tasks, do not batch a focus click with the `---` shortcut. "
            "First focus the intended anchor/insertion point, then inspect the next screenshot before inserting the divider."
        ),
        grounding=first_click.grounding,
        completion_check=action.completion_check,
        expected="The caret should move to the intended divider insertion point; no divider shortcut is typed until the next inspected step.",
        raw_text=action.raw_text,
    )


def _suppress_repeated_docs_divider_shortcut(case: TestCase, action: Action | None, history: list[StepResult]) -> Action | None:
    if not action or not _is_docs_divider_case(case):
        return action
    if not _action_contains_divider_shortcut(action):
        return action
    already_attempted = any(
        step.action and _action_contains_divider_shortcut(step.action)
        for step in history[-4:]
    )
    if not already_attempted:
        return action
    return Action(
        kind=ActionKind.WAIT,
        target="divider shortcut already attempted",
        thought=(
            "A Markdown divider shortcut has already been attempted recently. "
            "Do not type `---` again; wait and inspect whether the thin rendered divider is already visible between the anchors."
        ),
        expected="The next screenshot should be inspected for an existing rendered divider instead of inserting another divider.",
        raw_text=action.raw_text,
    )


def _action_contains_divider_shortcut(action: Action) -> bool:
    candidates = action.sub_actions if action.kind == ActionKind.BATCH else [action]
    return any(item.kind == ActionKind.TYPE_TEXT and item.text.strip() == "---" for item in candidates)


def _is_docs_divider_case(case: TestCase) -> bool:
    text = " ".join([case.id, case.name, case.instruction, case.stage]).lower()
    return (case.product or "").lower() == "docs" and _contains_any(text, ["分割线", "divider"])


def _is_divider_menu_loop_action(action: Action) -> bool:
    candidates = action.sub_actions if action.kind == ActionKind.BATCH else [action]
    for item in candidates:
        text = " ".join([item.target, item.thought, item.raw_text, str(item.grounding.get("evidence") or "")]).lower()
        if item.kind == ActionKind.SCROLL and _contains_any(text, ["menu", "菜单", "pop-up", "popup", "insert", "插入"]):
            return True
        if item.kind == ActionKind.CLICK and _contains_any(text, ["更多", "more"]) and _contains_any(
            text, ["menu", "菜单", "insert", "插入", "divider", "分割线"]
        ):
            return True
    return False


def _is_docs_structure_after_find_case(case: TestCase) -> bool:
    if (case.product or "").lower() != "docs":
        return False
    # Strip quoted content from instruction so that paragraph text identifiers
    # (e.g. "DOCS-DEMO-DIVIDER-BEFORE-20260506") don't false-positive match.
    instruction_unquoted = re.sub(r'[\u201c"][^\u201d"]*[\u201d"]', "", case.instruction)
    text = " ".join([case.id, case.name, instruction_unquoted, case.stage]).lower()
    return _contains_any(text, ["表格", "table", "分割线", "divider"])


def _is_docs_structure_insertion_point_action(action: Action) -> bool:
    text = " ".join([action.target, action.thought, action.raw_text]).lower()
    if _contains_any(
        text,
        [
            "table cell",
            "header cell",
            "data cell",
            "cell of",
            "cell in",
            "单元格",
            "表头格",
            "数据格",
            "表格内",
        ],
    ):
        return False
    return _contains_any(
        text,
        [
            "trailing end",
            "line end",
            "end of",
            "insertion point",
            "anchor line",
            "after the anchor",
            "cursor",
            "caret",
            "行尾",
            "末尾",
            "插入点",
            "锚点",
            "光标",
            "之后",
        ],
    )


def _is_slash_text_action(action: Action) -> bool:
    if action.kind == ActionKind.HOTKEY and action.key.strip() == "/":
        return True
    if action.kind == ActionKind.TYPE_TEXT and action.text.strip().lower() in {"/", "/表格", "/table", "/分割线", "/divider"}:
        return True
    if action.kind != ActionKind.BATCH:
        return False
    return any(_is_slash_text_action(sub_action) for sub_action in action.sub_actions)


def _is_docs_structure_esc_action(action: Action | None) -> bool:
    return bool(action and action.kind == ActionKind.HOTKEY and (action.key or "").lower() == "esc")


def _is_docs_bold_format_case(case: TestCase) -> bool:
    text = " ".join([case.id, case.name, case.instruction, case.stage]).lower()
    return (case.product or "").lower() == "docs" and ("加粗" in text or "bold" in text)


def _is_docs_bold_toggle_action(action: Action) -> bool:
    if action.kind == ActionKind.HOTKEY:
        return (action.key or "").replace("+", " ").strip().lower() in {"command b", "cmd b", "meta b"}
    if action.kind != ActionKind.CLICK:
        return False
    text = " ".join([action.target, action.thought, action.raw_text, str(action.grounding.get("evidence") or "")]).lower()
    return _contains_any(text, ["bold", "加粗", " b button", " b 控件", "粗体"])


def _same_docs_bold_toggle_target(previous: Action, current: Action) -> bool:
    previous_text = _docs_bold_toggle_target_text(previous)
    current_text = _docs_bold_toggle_target_text(current)
    if not previous_text or not current_text:
        return True
    return previous_text == current_text


def _docs_bold_toggle_target_text(action: Action) -> str:
    text = " ".join([action.target, action.thought, action.raw_text, str(action.grounding.get("evidence") or "")])
    quoted = re.findall(r"[“\"]([^”\"]{2,})[”\"]", text)
    if quoted:
        return quoted[-1].strip().lower()
    target = (action.target or "").strip().lower()
    target = re.sub(
        r"\b(selected|exact|target|phrase|text|word|span|bold|button|control|toolbar|b)\b",
        " ",
        target,
    )
    target = re.sub(r"(选中|目标|短语|文本|词语|加粗|粗体|按钮|控件)", " ", target)
    target = re.sub(r"\s+", " ", target).strip(" ：:，,。.;；'\"")
    if 2 <= len(target) <= 40:
        return target
    return ""


def _is_feishu_docs_host_name(value: str) -> bool:
    return _contains_any(value or "", ["飞书", "feishu", "lark", "docs", "云文档", "safari", "chrome", "arc"])


def _suppress_early_docs_table_repair_finish(case: TestCase, action: Action, steps: list[StepResult]) -> Action:
    if not action.is_terminal:
        return action
    if not _is_explicit_docs_table_repair_case(case):
        return action
    if _has_table_repair_edit(steps):
        return action
    return Action(
        kind=ActionKind.WAIT,
        target="suppressed early table repair finish",
        thought=(
            "The model attempted to finish a dirty table-repair case before any real edit. "
            "Continue from the visible table and repair stacked header/data text before finishing."
        ),
        expected="The next step should perform a real table repair action instead of finishing.",
        raw_text=action.raw_text,
    )


def _is_explicit_docs_table_repair_case(case: TestCase) -> bool:
    if (case.product or "").lower() != "docs":
        return False
    text = " ".join([case.instruction, case.name, case.expected, str(case.verification.get("assertion") or "")]).lower()
    return _contains_any(text, ["表格", "table"]) and _contains_any(
        text,
        [
            "堆在同一",
            "stacked",
            "必须修复",
            "must repair",
            "必须在不同",
            "separate row",
            "横向行边界",
            "row boundary",
        ],
    )


def _has_table_repair_edit(steps: list[StepResult]) -> bool:
    actions: list[Action] = []
    for step in steps:
        if step.action:
            actions.extend(_flatten_actions_for_runner(step.action))
    for item in actions:
        if item.kind == ActionKind.TYPE_TEXT and item.text:
            return True
        if item.kind == ActionKind.HOTKEY and (item.key or "").lower() in {
            "command x",
            "command v",
            "backspace",
            "delete",
        }:
            return True
        text = " ".join([item.target, item.thought, item.raw_text]).lower()
        if item.kind == ActionKind.CLICK and _contains_any(text, ["paste", "粘贴", "delete", "删除", "move", "移动"]):
            return True
    return False


def _flatten_actions_for_runner(action: Action) -> list[Action]:
    if action.kind != ActionKind.BATCH:
        return [action]
    result: list[Action] = []
    for item in action.sub_actions:
        result.extend(_flatten_actions_for_runner(item))
    return result


def _capture_with_retries(screen: Screen, attempts: int = 4, delay: float = 1.0):
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return screen.capture()
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(delay)
    if last_error:
        raise last_error
    return screen.capture()


def _prepare_screen_for_case(screen: Screen) -> dict[str, object]:
    ensure = getattr(screen, "ensure_app_window_visible", None)
    if callable(ensure):
        try:
            ensure()
        except Exception as exc:
            return {"action": "ensure_app_window_visible", "ok": False, "error": str(exc)}
        return {"action": "ensure_app_window_visible", "ok": True}
    return {"action": "none"}


def _ensure_action_allowed(action: Action, case: TestCase, *, context: str = "Action") -> None:
    if action.kind == ActionKind.FINISHED or not case.allowed_actions:
        return
    allowed = {_normalize_allowed_action(item) for item in case.allowed_actions}
    if action.kind.value not in allowed:
        raise ValueError(f"{context} {action.kind.value} is not allowed for case {case.id}")


def _normalize_allowed_action(value: str) -> str:
    aliases = {
        "type": ActionKind.TYPE_TEXT.value,
        "type_text": ActionKind.TYPE_TEXT.value,
        "left_double": ActionKind.DOUBLE_CLICK.value,
        "double_click": ActionKind.DOUBLE_CLICK.value,
        "right_single": ActionKind.RIGHT_CLICK.value,
        "right_click": ActionKind.RIGHT_CLICK.value,
    }
    key = (value or "").strip().lower()
    return aliases.get(key, key)


def _first_grounding_check_field(action: Action, field: str) -> str:
    value = action.grounding_check.get(field)
    if value:
        return str(value)
    for sub_action in action.sub_actions:
        value = sub_action.grounding_check.get(field)
        if value:
            return str(value)
    return ""


def _vlm_metadata(vlm: VisionModel) -> dict[str, object]:
    value = getattr(vlm, "last_response", None)
    return dict(value) if isinstance(value, dict) else {}


def _available_rule_names(rules_root: Path) -> list[str]:
    return sorted(path.stem for path in rules_root.glob("*.md") if path.name != "index.md")
