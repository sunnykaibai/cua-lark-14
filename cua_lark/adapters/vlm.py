from __future__ import annotations

import base64
import io
import time
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI
from PIL import Image

from cua_lark.runtime.config import Settings, env


class VisionModel(Protocol):
    def complete(
        self,
        image: Image.Image,
        prompt: str,
        system_prompt: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        ...


@dataclass
class OpenAIVisionModel:
    client: OpenAI
    model: str
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = 700
    max_completion_tokens: int | None = None
    thinking: dict[str, Any] | None = None
    reasoning_effort: str | None = None
    retries: int = 4
    last_response: dict[str, Any] | None = None

    def complete(
        self,
        image: Image.Image,
        prompt: str,
        system_prompt: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        self.last_response = None
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_encode(image)}"}},
                ],
            }
        )
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                request = self._request_kwargs(messages, options=options)
                response = self.client.chat.completions.create(**request)
                message = response.choices[0].message
                content = message.content or ""
                self.last_response = self._response_metadata(response, request, content)
                return content
            except Exception as exc:
                last_error = exc
                if attempt < self.retries and _is_rate_limit(exc):
                    time.sleep(3)
                    continue
                raise
        raise RuntimeError(last_error or "VLM call failed")

    def _request_kwargs(self, messages: list[dict[str, Any]], *, options: dict[str, Any] | None = None) -> dict[str, Any]:
        options = options or {}
        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        temperature = options.get("temperature", self.temperature)
        top_p = options.get("top_p", self.top_p)
        max_completion_tokens = options.get("max_completion_tokens", self.max_completion_tokens)
        max_tokens = options.get("max_tokens", self.max_tokens)
        if temperature is not None:
            request["temperature"] = temperature
        if top_p is not None:
            request["top_p"] = top_p
        if max_completion_tokens is not None:
            request["max_completion_tokens"] = max_completion_tokens
        elif max_tokens is not None:
            request["max_tokens"] = max_tokens

        extra_body: dict[str, Any] = {}
        thinking = options.get("thinking", self.thinking)
        reasoning_effort = options.get("reasoning_effort", self.reasoning_effort)
        if thinking is not None:
            extra_body["thinking"] = thinking
        if reasoning_effort is not None and not _thinking_disabled(thinking):
            extra_body["reasoning_effort"] = reasoning_effort
        if extra_body:
            request["extra_body"] = extra_body
        return request

    def _response_metadata(self, response: Any, request: dict[str, Any], content: str) -> dict[str, Any]:
        choice = response.choices[0]
        message = choice.message
        message_dump = message.model_dump() if hasattr(message, "model_dump") else {}
        usage = response.usage.model_dump() if response.usage and hasattr(response.usage, "model_dump") else response.usage
        request_summary = {
            key: request.get(key)
            for key in ["model", "temperature", "top_p", "max_tokens", "max_completion_tokens", "extra_body"]
            if key in request
        }
        return {
            "content": content,
            "reasoning_content": message_dump.get("reasoning_content") or "",
            "message_keys": sorted(key for key, value in message_dump.items() if value is not None),
            "finish_reason": choice.finish_reason,
            "usage": usage,
            "request": request_summary,
        }


@dataclass
class OpenAIResponsesVisionModel:
    client: OpenAI
    model: str
    reasoning_effort: str | None = None
    max_output_tokens: int | None = 8192
    temperature: float | None = None
    top_p: float | None = None
    store: bool = False
    retries: int = 2
    last_response: dict[str, Any] | None = None

    def complete(
        self,
        image: Image.Image,
        prompt: str,
        system_prompt: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        self.last_response = None
        request = self._request_kwargs(image, prompt, system_prompt, options=options)
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self.client.responses.create(**request)
                content = getattr(response, "output_text", "") or _response_output_text(response)
                self.last_response = self._response_metadata(response, request, content)
                return content
            except Exception as exc:
                last_error = exc
                if attempt < self.retries and _is_rate_limit(exc):
                    time.sleep(3)
                    continue
                raise
        raise RuntimeError(last_error or "VLM responses call failed")

    def _request_kwargs(
        self,
        image: Image.Image,
        prompt: str,
        system_prompt: str,
        *,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        options = options or {}
        request: dict[str, Any] = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{_encode(image)}"},
                    ],
                }
            ],
            "store": self.store,
        }
        if system_prompt:
            request["instructions"] = system_prompt
        max_output_tokens = options.get("max_output_tokens", self.max_output_tokens)
        reasoning_effort = options.get("reasoning_effort", self.reasoning_effort)
        temperature = options.get("temperature", self.temperature)
        top_p = options.get("top_p", self.top_p)
        if max_output_tokens is not None:
            request["max_output_tokens"] = max_output_tokens
        if reasoning_effort is not None:
            request["reasoning"] = {"effort": reasoning_effort}
        if temperature is not None:
            request["temperature"] = temperature
        if top_p is not None:
            request["top_p"] = top_p
        return request

    def _response_metadata(self, response: Any, request: dict[str, Any], content: str) -> dict[str, Any]:
        response_dump = response.model_dump() if hasattr(response, "model_dump") else {}
        request_summary = {
            key: request.get(key)
            for key in ["model", "reasoning", "max_output_tokens", "temperature", "top_p", "store"]
            if key in request
        }
        output = response_dump.get("output") or []
        return {
            "content": content,
            "reasoning_content": "",
            "message_keys": sorted(response_dump.keys()),
            "finish_reason": response_dump.get("status") or getattr(response, "status", ""),
            "usage": response_dump.get("usage"),
            "output_types": [item.get("type") for item in output if isinstance(item, dict)],
            "request": request_summary,
        }


class EchoVisionModel:
    """Dry-run model for parser/report tests."""

    def __init__(self, response: str):
        self.response = response
        self.last_response: dict[str, Any] | None = None

    def complete(
        self,
        image: Image.Image,
        prompt: str,
        system_prompt: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        self.last_response = {
            "content": self.response,
            "reasoning_content": "",
            "message_keys": ["content"],
            "finish_reason": "echo",
            "usage": {},
            "request": {},
        }
        return self.response


def build_vlm(settings: Settings, backend: str | None = None) -> VisionModel:
    vlm = settings.vlm
    selected = backend or vlm.get("default_backend") or "seed-2.0"
    if selected == "minimax":
        return OpenAIVisionModel(
            client=OpenAI(
                api_key=env("MINIMAX_API_KEY"),
                base_url=env("MINIMAX_BASE_URL", "https://models.sjtu.edu.cn/api/v1"),
                timeout=float(env("MINIMAX_TIMEOUT", "120")),
                max_retries=int(env("MINIMAX_MAX_RETRIES", "2")),
            ),
            model=env("MINIMAX_MODEL", "minimax"),
        )

    config_key = selected.replace("-", "_").replace(".", "_")
    cfg = vlm.get(config_key) or vlm.get("seed_2_0") or {}
    if cfg.get("wire_api") == "responses":
        return OpenAIResponsesVisionModel(
            client=OpenAI(
                api_key=cfg.get("api_key"),
                base_url=cfg.get("base_url"),
                timeout=cfg.get("timeout", 120),
                max_retries=cfg.get("max_retries", 0),
            ),
            model=cfg.get("model", selected),
            reasoning_effort=cfg.get("reasoning_effort"),
            max_output_tokens=cfg.get("max_output_tokens", 8192),
            temperature=cfg.get("temperature"),
            top_p=cfg.get("top_p"),
            store=bool(cfg.get("store", False)),
            retries=int(cfg.get("retries", 2)),
        )
    return OpenAIVisionModel(
        client=OpenAI(
            api_key=cfg.get("api_key"),
            base_url=cfg.get("base_url"),
            timeout=cfg.get("timeout", 30),
            max_retries=cfg.get("max_retries", 3),
        ),
        model=cfg.get("model", selected),
        temperature=cfg.get("temperature"),
        top_p=cfg.get("top_p"),
        max_tokens=cfg.get("max_tokens", 700),
        max_completion_tokens=cfg.get("max_completion_tokens"),
        thinking=cfg.get("thinking"),
        reasoning_effort=cfg.get("reasoning_effort"),
    )


def _encode(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _is_rate_limit(error: Exception) -> bool:
    text = str(error).lower()
    return any(token in text for token in ["429", "rate limit", "ratelimit", "too many requests", "tpm"])


def _thinking_disabled(value: object) -> bool:
    return isinstance(value, dict) and str(value.get("type") or "").lower() == "disabled"


def _response_output_text(response: Any) -> str:
    dump = response.model_dump() if hasattr(response, "model_dump") else {}
    parts: list[str] = []
    for item in dump.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                parts.append(str(content.get("text") or ""))
    return "".join(parts)
