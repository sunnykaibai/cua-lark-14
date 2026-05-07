from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Status(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    RUNNING = "running"


class ActionKind(str, Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    SCROLL = "scroll"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    WAIT = "wait"
    FINISHED = "finished"
    BATCH = "batch"


@dataclass(frozen=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True)
class Box:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def center(self) -> Point:
        return Point(round((self.x1 + self.x2) / 2), round((self.y1 + self.y2) / 2))


@dataclass
class Action:
    kind: ActionKind
    point: Point | None = None
    end_point: Point | None = None
    text: str = ""
    key: str = ""
    direction: str = ""
    clear_existing: bool | None = None
    target: str = ""
    thought: str = ""
    grounding: dict[str, Any] = field(default_factory=dict)
    grounding_check: dict[str, Any] = field(default_factory=dict)
    completion_check: dict[str, Any] = field(default_factory=dict)
    expected: str = ""
    raw_text: str = ""
    sub_actions: list["Action"] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.kind == ActionKind.FINISHED


@dataclass
class TestCase:
    id: str
    name: str
    instruction: str
    expected: str
    product: str = ""
    phase: str = ""
    stage: str = ""
    verification: dict[str, Any] = field(default_factory=dict)
    allowed_actions: list[str] = field(default_factory=list)
    explicit_allowed_actions: list[str] = field(default_factory=list)
    action_policy_source: str = ""
    input_materials: list[dict[str, str]] = field(default_factory=list)
    setup_instruction: str = ""
    setup_expected: str = ""
    setup_max_steps: int = 6


@dataclass
class GoalContract:
    goal: str = ""
    completion_evidence: list[str] = field(default_factory=list)
    non_completion_evidence: list[str] = field(default_factory=list)
    must_not: list[str] = field(default_factory=list)
    raw: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    index: int
    action: Action | None
    before: str = ""
    after: str = ""
    grounding_crop: str = ""
    elements_overlay: str = ""
    grounding_check_image: str = ""
    system_prompt: str = ""
    prompt: str = ""
    rules_prompt: str = ""
    rule_selection_prompt: str = ""
    rule_selection_raw: str = ""
    rule_selection_reasoning: str = ""
    rule_selection_metadata: dict[str, Any] = field(default_factory=dict)
    rule_selection_reason: str = ""
    rule_selection_fallback_used: bool = False
    rule_selection_error: str = ""
    selected_rules: list[str] = field(default_factory=list)
    selected_rule_paths: list[str] = field(default_factory=list)
    selected_rule_hashes: dict[str, str] = field(default_factory=dict)
    grounding_check_prompt: str = ""
    passed: bool = False
    message: str = ""
    visual_change: dict[str, Any] = field(default_factory=dict)
    screenshot: dict[str, Any] = field(default_factory=dict)
    raw_model: str = ""
    reasoning: str = ""
    vlm_metadata: dict[str, Any] = field(default_factory=dict)
    timing: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseResult:
    case: TestCase
    status: Status
    setup_steps: list[StepResult] = field(default_factory=list)
    steps: list[StepResult] = field(default_factory=list)
    failure: str = ""
    final_screenshot: str = ""
    cli_verifier_response: str = ""
    cli_verifier_metadata: dict[str, Any] = field(default_factory=dict)
    verifier_prompt: str = ""
    verifier_response: str = ""
    verifier_reasoning: str = ""
    verifier_metadata: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    process_quality: dict[str, Any] = field(default_factory=dict)
    goal_contract: GoalContract | None = None
    screen_preparation: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    finished_at: str = ""

    @property
    def passed(self) -> bool:
        return self.status == Status.PASSED


@dataclass
class RunInfo:
    suite: str
    round_id: str
    root: Path
    cases_dir: Path
    started_at: str


TestCase.__test__ = False
