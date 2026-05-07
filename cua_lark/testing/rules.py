from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


DEFAULT_RULE_NAMES: tuple[str, ...] = (
    "feishu_shell",
    "live_object",
    "composer",
    "im_chat",
    "emoji_picker",
    "mention_picker",
    "search_find",
    "conversation_ops",
    "screenshot_overlay",
)

DEFAULT_DOCS_RULE_NAMES: tuple[str, ...] = (
    "feishu_shell",
    "live_object",
    "docs_shell",
    "docs_body_edit",
    "docs_search_navigation",
)

DEFAULT_IM_RULE_NAMES: tuple[str, ...] = DEFAULT_RULE_NAMES


@dataclass(frozen=True)
class RuleModule:
    name: str
    path: Path
    text: str
    sha256: str


def default_rules_root(new_root: Path) -> Path:
    return new_root / "cua_lark" / "rules"


def load_rule_bundle(names: list[str] | tuple[str, ...], rules_root: Path) -> list[RuleModule]:
    modules: list[RuleModule] = []
    seen: set[str] = set()
    for raw_name in names:
        name = _normalize_rule_name(raw_name)
        if not name or name in seen:
            continue
        path = rules_root / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Rule module not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
        modules.append(
            RuleModule(
                name=name,
                path=path,
                text=text,
                sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )
        )
        seen.add(name)
    return modules


def render_rules_prompt(modules: list[RuleModule]) -> str:
    if not modules:
        return ""
    sections: list[str] = []
    for module in modules:
        sections.extend([f"## Rule: {module.name}", _strip_leading_h1(module.text)])
    return "\n\n".join(sections)


def rule_names(modules: list[RuleModule]) -> list[str]:
    return [module.name for module in modules]


def rule_paths(modules: list[RuleModule], *, relative_to: Path | None = None) -> list[str]:
    paths: list[str] = []
    for module in modules:
        path = module.path
        if relative_to is not None:
            try:
                path = path.relative_to(relative_to)
            except ValueError:
                pass
        paths.append(str(path))
    return paths


def rule_hashes(modules: list[RuleModule]) -> dict[str, str]:
    return {module.name: module.sha256 for module in modules}


def _normalize_rule_name(value: str) -> str:
    text = (value or "").strip()
    if text.endswith(".md"):
        text = text[:-3]
    return text


def _strip_leading_h1(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].lstrip().startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()
