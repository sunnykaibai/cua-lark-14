# CUA-Lark New Construction Agent Instructions

These are the active project rules when working inside
`/Users/ishuo/Documents/研一下/飞书挑战赛/00-new_construction`.

This directory is now the active CUA-Lark development workspace. The older
`cua-lark-14` directory is sealed as historical evidence/reference material and
should not receive new feature work unless the user explicitly asks to inspect
or migrate something from it.

## Required Context

At the start of a task in this workspace, read the minimum relevant context:

1. `AGENTS.md`
2. `README.md`
3. `docs/task-understanding.md`
4. Relevant scenario prompt under `cua_lark/scenarios/`
5. Relevant test case YAML, usually from `tests/test_cases/`
6. `work_dairy/README.md` when the task affects design, tests, or architecture

## Project Goal

Build a pure-vision Computer-Use Agent test framework for Feishu/Lark desktop.
The agent should operate like a human tester:

1. capture the current screen or app window
2. let the VLM understand the visible UI and the natural-language task
3. choose one next GUI action
4. execute through the normalized action/executor path
5. observe again through a fresh screenshot
6. verify and report the result

## Direction: Pure Vision

1. Do not add semantic guard systems, case-specific fallbacks, hidden operation recipes, or hardcoded recovery paths.
2. Recovery and alternative paths should come from the VLM reading the next screenshot and history.
3. Improve failures by improving screenshot quality, prompt clarity, action schema, coordinate conversion, grounding evidence, VLM-visible history, or test data.
4. Do not use Accessibility Tree, DOM, or API state as a replacement for visual decision-making unless the user explicitly changes the direction.
5. Coordinate conversion, action parsing, execution, screenshots, and reporting must stay on the shared normalized path.

## Execution Prompt Boundary

Execution-time VLM prompts may include only:

- current screenshot
- user's natural-language `instruction`
- allowed actions
- recent execution history
- general/scenario operation protocol

Execution-time VLM prompts must not include:

- `expected`
- `verification.assertion`
- hidden pass/fail criteria
- internal test implementation notes

`expected` and `verification.assertion` are reserved for final verification and reports.

## Canonical Entry Points

- Run tests with `scripts/run_test.py`.
- Workspace configuration lives in `configs/config.yaml`; do not rely on the parent workspace's config by default.
- Main loop: `cua_lark/testing/runner.py`.
- Prompt builder: `cua_lark/testing/prompt.py`.
- Action parsing and coordinate conversion:
  - `cua_lark/domain/action_parser.py`
  - `cua_lark/domain/coordinates.py`
- GUI execution: `cua_lark/adapters/gui.py`.
- Screenshot and visual evidence: `cua_lark/adapters/screen.py`.
- Reports: `cua_lark/reporting/writer.py`.

## Test Results

Every test run must create a new round directory:

```text
results/<round-name>-<YYYYMMDD-HHMMSS>/
  README.md
  summary.json
  cases/
    <case-id>__<case-name>/
      record.json
      steps.md
      NN-before.png
      NN-after.png
      NN-grounding.png
      final.png
```

Use the per-run `README.md` as the review entrypoint and per-case `steps.md`
for step-level diagnosis.

When a test run is part of an optimization comparison or ablation, the round
name must start with `MMDD-HHMM`, for example
`0426-1634-grounding-check-region-crop`, so result folders sort naturally in
review order.

## Test Case Authoring

1. `instruction` must be a natural user request, not an internal operation plan.
2. Do not put UI location hints in `instruction`, such as "右上角", "左侧列表", "点击 X 按钮", or step-by-step control discovery.
3. Do not put validation wording in `instruction`, such as "确认", "验证", or "判定通过".
4. Put expected outcomes in `expected` and `verification.assertion`.
5. A test case should complete a realistic user goal, not stop at an intermediate menu, picker, or tab.
6. Large suites should define `test_stages`; each case should have a `test_stage`.

## VLM Action Requirements

1. The VLM action response must name concrete target objects in `Thought` and `Grounding`.
2. Avoid vague targets such as "message", "button", "emoji", or "control".
3. Scroll actions must target a concrete scrollable area visible in the screenshot.
4. If the target is not visible, the next action should visually search or navigate toward that concrete target.
5. For Feishu IM @ mentions, create a real mention token through the UI; do not type a plain `@Name message`.
6. For IM reactions or message operations, operate on real live chat bubbles, not content depicted inside screenshots, cards, or images.

## Documentation

1. Keep `README.md` as the practical entrypoint.
2. Keep `docs/task-understanding.md` aligned with the competition goal and current architecture.
3. Keep detailed execution dossiers under `docs/execution-dossiers/`. These dossiers explain how each execution stage or subsystem currently works, including VLM inputs/outputs, action parsing, verification, report writing, and field usage.
4. When code changes affect runner behavior, prompt construction, action schema, verification, reporting, scenario rules, or test case format, update the relevant execution dossier in the same work session.
5. Keep optimization comparisons under `ablation/`. Every meaningful optimization should have an ablation record that states the baseline, changed variable, command, report paths, metrics, and whether the optimization is worth keeping. Ablation record filenames and related optimization test round names must start with `MMDD-HHMM`, for example `ablation/04-26/0426-1640-grounding-check.md` and `results/0426-1640-grounding-check-...`, so they sort naturally by time.
6. Add important work records under `work_dairy/`.
7. Update `work_dairy/README.md` when adding a new work record.
8. Do not bury long scenario-specific instructions inside runner code; put reusable operation protocol in `cua_lark/scenarios/`.

## Skills

Project skills live under `.agents/skills/`.

Use these when relevant:

- `collect-info`: reading and summarizing provided materials or research inputs
- `research-project-orchestrator`: planning multi-phase project work
- `push-certain-phase`: executing a defined project phase
- `where-are-we`: restoring project state and next steps
- `auto-tackle`: sustained autonomous debugging and iteration when the user asks to keep going until solved

## Git

1. Use SSH for push operations.
2. Remote repository: `git@github.com:sunnykaibai/cua-lark-14.git`
3. Default branch: `main`

## Development Notes

1. Prefer small, reviewable modules.
2. Do not reintroduce old runner complexity unless it directly helps the pure-vision loop.
3. When absorbing old code, keep only reusable capabilities such as screenshot metadata, coordinate conversion, VLM calls, visual diff, grounding evidence, and report formatting.
4. Do not copy old logs, screenshots, or historical outputs into new source modules.
5. Use the `feishu` conda environment when running real GUI tests, if applicable.
