from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from cua_lark.domain.models import TestCase


QUOTE = re.compile(r"[“\"]([^”\"]+)[”\"]")


def verify_im_message_with_lark_cli(case: TestCase, start: datetime, end: datetime) -> dict[str, Any]:
    if not _looks_like_im_send_case(case):
        return {"status": "skipped", "reason": "not_im_send_case"}
    query = _message_query(case)
    if not query:
        return {"status": "skipped", "reason": "no_searchable_message_text"}

    command = [
        "lark-cli",
        "im",
        "+messages-search",
        "--as",
        "user",
        "--query",
        query,
        "--chat-type",
        "p2p",
        "--start",
        _iso_with_timezone(start),
        "--end",
        _iso_with_timezone(end),
        "--page-size",
        "20",
        "--format",
        "json",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=45, check=False)
    except FileNotFoundError:
        return {"status": "skipped", "reason": "lark_cli_not_found", "query": query}
    except subprocess.TimeoutExpired as exc:
        return {"status": "skipped", "reason": "lark_cli_timeout", "query": query, "error": str(exc)}

    metadata: dict[str, Any] = {
        "command": _redacted_command(command),
        "query": query,
        "start": _iso_with_timezone(start),
        "end": _iso_with_timezone(end),
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip(),
    }
    if completed.returncode != 0:
        return {**metadata, "status": "skipped", "reason": "lark_cli_error", "stdout": completed.stdout.strip()}

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {**metadata, "status": "skipped", "reason": "invalid_json", "error": str(exc), "stdout": completed.stdout[:1000]}

    messages = _messages(payload)
    matches = [_compact_message(item) for item in messages if _matches_case(case, query, item)]
    metadata.update(
        {
            "identity": payload.get("identity"),
            "total": (payload.get("data") or {}).get("total"),
            "message_count": len(messages),
            "match_count": len(matches),
            "matches": matches[:5],
        }
    )
    if matches:
        return {**metadata, "status": "passed", "reason": "matching_message_found_after_test_start"}
    return {**metadata, "status": "failed", "reason": "no_matching_message_after_test_start"}


def format_cli_verifier_response(result: dict[str, Any]) -> str:
    status = result.get("status", "skipped")
    reason = result.get("reason", "")
    query = result.get("query", "")
    start = result.get("start", "")
    end = result.get("end", "")
    matches = result.get("matches") or []
    lines = [
        f"CLIStatus: {status}",
        f"Reason: {reason}",
        f"Query: {query}",
        f"Window: {start} -> {end}",
        f"MessageCount: {result.get('message_count', '')}",
        f"MatchCount: {result.get('match_count', '')}",
    ]
    if matches:
        lines.append("Matches:")
        for item in matches:
            lines.append(
                f"- {item.get('create_time')} {item.get('msg_type')} {item.get('content')} "
                f"message_id={item.get('message_id')}"
            )
    return "\n".join(lines)


def _looks_like_im_send_case(case: TestCase) -> bool:
    text = " ".join([case.product, case.stage, case.name, case.instruction]).lower()
    if any(term in text for term in ["标记", "reaction", "反应", "未读", "完成"]):
        return False
    if any(term in text for term in ["云文档", "图片", "文件", "名片", "附件", "分享"]):
        return False
    return "im" in text or "发送" in text or "发给" in text or "回复" in text


def _message_query(case: TestCase) -> str:
    if "回复" in (case.instruction or ""):
        matches = QUOTE.findall(case.instruction or "")
        if matches:
            return matches[-1].strip()
    for source in [case.instruction, case.expected, case.name]:
        match = QUOTE.search(source or "")
        if match:
            return _searchable_query(match.group(1).strip())
    return ""


def _searchable_query(value: str) -> str:
    url_match = re.search(r"https?://[^\s”\"]+", value or "")
    if not url_match:
        return value
    parsed = urlparse(url_match.group(0))
    return parsed.netloc or url_match.group(0)


def _matches_case(case: TestCase, query: str, message: dict[str, Any]) -> bool:
    content = str(message.get("content") or "")
    if message.get("deleted"):
        return False
    if query not in content:
        return False
    if _requires_emoji(case):
        return _contains_emoji_marker(content, query)
    return True


def _requires_emoji(case: TestCase) -> bool:
    text = " ".join([case.name, case.instruction, case.expected]).lower()
    return "表情" in text or "emoji" in text


def _contains_emoji_marker(content: str, query: str) -> bool:
    suffix = content.replace(query, "", 1).strip()
    return bool(suffix)


def _messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else {}
    messages = data.get("messages") if isinstance(data, dict) else []
    return [item for item in messages if isinstance(item, dict)]


def _compact_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": message.get("message_id"),
        "chat_id": message.get("chat_id"),
        "chat_type": message.get("chat_type"),
        "msg_type": message.get("msg_type"),
        "content": message.get("content"),
        "create_time": message.get("create_time"),
        "sender": (message.get("sender") or {}).get("name") or (message.get("sender") or {}).get("id"),
    }


def _iso_with_timezone(value: datetime) -> str:
    return value.astimezone().isoformat(timespec="seconds")


def _redacted_command(command: list[str]) -> list[str]:
    return list(command)
