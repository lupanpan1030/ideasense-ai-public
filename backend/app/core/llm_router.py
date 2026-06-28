from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

try:
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials
except Exception:  # pragma: no cover - optional dependency
    SigV4Auth = None
    AWSRequest = None
    Credentials = None


SUPPORTED_PROVIDERS = ("openai", "deepseek", "qwen", "gemini", "bedrock")
DEEPSEEK_PRO_TASKS = {"stage_summary", "report", "dvf_scoring"}
QWEN_PRO_TASKS = {"stage_summary", "report", "dvf_scoring"}
GEMINI_PRO_TASKS = {"stage_summary", "report", "dvf_scoring"}
TASK_DEFAULT_BEATS_GLOBAL_DEFAULT = {"followup_compose", "question_compose"}
DEFAULT_PROVIDER_ORDER = {
    "ai_assist": ["deepseek", "qwen", "gemini", "bedrock", "openai"],
    "answer_gate": ["deepseek", "qwen", "gemini", "bedrock", "openai"],
    "extract": ["deepseek", "qwen", "gemini", "bedrock", "openai"],
    "followup_compose": ["qwen", "gemini", "deepseek", "bedrock", "openai"],
    "question_compose": ["qwen", "gemini", "deepseek", "bedrock", "openai"],
    "question_rewrite": ["qwen", "deepseek", "gemini", "bedrock", "openai"],
    "router": ["deepseek", "qwen", "gemini", "bedrock", "openai"],
    "stage_summary": ["deepseek", "qwen", "gemini", "bedrock", "openai"],
    "report": ["qwen", "deepseek", "gemini", "bedrock", "openai"],
    "dvf_scoring": ["deepseek", "qwen", "gemini", "bedrock", "openai"],
    "qa_digest": ["deepseek", "qwen", "gemini", "bedrock", "openai"],
}


@dataclass(frozen=True)
class LLMResult:
    content: str
    provider: str
    model: str


@dataclass(frozen=True)
class LLMStream:
    provider: str
    model: str
    stream: Any


class LLMError(RuntimeError):
    pass


def _split_chain(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    cleaned = base_url.strip().rstrip("/")
    if not cleaned:
        return None
    if not cleaned.endswith("/v1"):
        cleaned = f"{cleaned}/v1"
    return cleaned


def _join_system_messages(messages: list[dict[str, Any]]) -> str | None:
    parts: list[str] = []
    for message in messages:
        if message.get("role") != "system":
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    if not parts:
        return None
    return "\n".join(parts)


def _openai_model(task: str) -> str:
    fallback = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    if task == "answer_gate":
        return (os.getenv("OPENAI_ANSWER_GATE_MODEL") or fallback).strip() or fallback
    if task == "question_rewrite":
        return (
            os.getenv("OPENAI_QUESTION_REWRITE_MODEL") or fallback
        ).strip() or fallback
    if task == "question_compose":
        return (
            os.getenv("OPENAI_QUESTION_COMPOSE_MODEL") or fallback
        ).strip() or fallback
    if task == "followup_compose":
        return (
            os.getenv("OPENAI_FOLLOWUP_COMPOSE_MODEL") or fallback
        ).strip() or fallback
    if task == "extract":
        return (os.getenv("OPENAI_EXTRACT_MODEL") or fallback).strip() or fallback
    if task == "router":
        return (os.getenv("OPENAI_ROUTER_MODEL") or fallback).strip() or fallback
    if task in {"stage_summary", "report", "dvf_scoring", "qa_digest"}:
        return (os.getenv("OPENAI_REPORT_MODEL") or fallback).strip() or fallback
    return fallback


def _env_value(key: str) -> str | None:
    value = os.getenv(key, "").strip()
    return value or None


def _deepseek_model(task: str) -> str | None:
    task_override = _env_value(f"DEEPSEEK_{task.upper()}_MODEL")
    if task_override:
        return task_override
    default_model = _env_value("DEEPSEEK_MODEL")
    pro_model = _env_value("DEEPSEEK_PRO_MODEL")
    if task in DEEPSEEK_PRO_TASKS and pro_model:
        return pro_model
    return default_model or pro_model


def _qwen_model(task: str) -> str | None:
    task_override = _env_value(f"QWEN_{task.upper()}_MODEL")
    if task_override:
        return task_override
    default_model = _env_value("QWEN_MODEL")
    pro_model = _env_value("QWEN_PRO_MODEL")
    if task in QWEN_PRO_TASKS and pro_model:
        return pro_model
    return default_model or pro_model


def _qwen_base_url() -> str | None:
    return _normalize_base_url(
        os.getenv(
            "QWEN_BASE_URL",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
    )


def _gemini_model(task: str | None = None) -> str | None:
    if task:
        task_override = _env_value(f"GEMINI_{task.upper()}_MODEL")
        if task_override:
            return task_override
    default_model = _env_value("GEMINI_MODEL")
    pro_model = _env_value("GEMINI_PRO_MODEL")
    if task in GEMINI_PRO_TASKS and pro_model:
        return pro_model
    return default_model or pro_model


def _bedrock_model(task: str) -> str | None:
    if task in {"stage_summary", "report", "dvf_scoring", "qa_digest"}:
        for key in ("BEDROCK_MODEL_ID_REPORT", "BEDROCK_MODEL_ID_STAGE_EVAL"):
            value = os.getenv(key, "").strip()
            if value:
                return value
    for key in ("BEDROCK_MODEL_ID_CHAT", "BEDROCK_MODEL_ID_DEFAULT", "BEDROCK_MODEL_ID"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return None


def _bedrock_fallback_model() -> str | None:
    return os.getenv("BEDROCK_MODEL_ID_FALLBACK", "").strip() or None


def _provider_available(provider: str, task: str) -> bool:
    provider = provider.lower()
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY", "").strip())
    if provider == "deepseek":
        return bool(os.getenv("DEEPSEEK_API_KEY", "").strip()) and bool(
            _deepseek_model(task)
        )
    if provider == "qwen":
        return bool(os.getenv("QWEN_API_KEY", "").strip()) and bool(_qwen_model(task))
    if provider == "gemini":
        return bool(os.getenv("GEMINI_API_KEY", "").strip()) and bool(
            _gemini_model(task)
        )
    if provider == "bedrock":
        if not _bedrock_model(task):
            return False
        if not os.getenv("AWS_REGION", "").strip():
            return False
        if not os.getenv("AWS_ACCESS_KEY_ID", "").strip():
            return False
        if not os.getenv("AWS_SECRET_ACCESS_KEY", "").strip():
            return False
        return SigV4Auth is not None and AWSRequest is not None and Credentials is not None
    return False


def _resolve_provider_chain(task: str) -> list[str]:
    explicit = _split_chain(os.getenv(f"LLM_PROVIDER_{task.upper()}"))
    if explicit:
        ordered = explicit
    elif task in TASK_DEFAULT_BEATS_GLOBAL_DEFAULT:
        ordered = DEFAULT_PROVIDER_ORDER.get(task, list(SUPPORTED_PROVIDERS))
    else:
        default = _split_chain(os.getenv("LLM_PROVIDER_DEFAULT"))
        if default:
            ordered = default
        else:
            ordered = DEFAULT_PROVIDER_ORDER.get(task, list(SUPPORTED_PROVIDERS))

    seen: set[str] = set()
    filtered: list[str] = []
    for provider in ordered:
        if provider not in SUPPORTED_PROVIDERS:
            continue
        if provider in seen:
            continue
        if _provider_available(provider, task):
            filtered.append(provider)
            seen.add(provider)
    return filtered


def has_available_provider(task: str) -> bool:
    return bool(_resolve_provider_chain(task))


def _http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return _http_post_body(url, data, headers)


def _http_post_body(url: str, body: bytes, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # pragma: no cover - passthrough
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise LLMError(f"HTTP {exc.code} {url}: {detail}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - passthrough
        raise LLMError(f"HTTP request failed: {exc}") from exc
    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise LLMError("Provider returned invalid JSON response.") from exc


async def _call_openai(
    messages: list[dict[str, Any]],
    model: str,
    api_key: str,
    base_url: str | None,
    temperature: float | None,
    response_format: str | None,
) -> str:
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0 if temperature is None else temperature,
    }
    if response_format == "json_object":
        kwargs["response_format"] = {"type": "json_object"}
    response = await client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content or ""
    if not content.strip():
        raise LLMError("OpenAI provider returned empty content.")
    return content


async def _call_openai_stream(
    messages: list[dict[str, Any]],
    model: str,
    api_key: str,
    base_url: str | None,
    temperature: float | None,
    response_format: str | None,
):
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0 if temperature is None else temperature,
        "stream": True,
    }
    if response_format == "json_object":
        kwargs["response_format"] = {"type": "json_object"}

    stream = await client.chat.completions.create(**kwargs)

    async def iterator():
        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content
            except Exception:
                delta = None
            if delta:
                yield delta

    return iterator()


def _build_gemini_payload(
    messages: list[dict[str, Any]],
    temperature: float | None,
    response_format: str | None,
) -> dict[str, Any]:
    system_text = _join_system_messages(messages)
    contents: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        if role == "system":
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if role == "assistant":
            gemini_role = "model"
        else:
            gemini_role = "user"
        contents.append({"role": gemini_role, "parts": [{"text": content}]})

    payload: dict[str, Any] = {"contents": contents}
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}
    if temperature is not None:
        payload["generationConfig"] = {"temperature": temperature}
    if response_format == "json_object":
        payload.setdefault("generationConfig", {})["response_mime_type"] = (
            "application/json"
        )
    return payload


async def _call_gemini(
    messages: list[dict[str, Any]],
    model: str,
    api_key: str,
    temperature: float | None,
    response_format: str | None,
) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )
    payload = _build_gemini_payload(messages, temperature, response_format)
    response = await asyncio.to_thread(
        _http_post_json, url, payload, {"Content-Type": "application/json"}
    )
    candidates = response.get("candidates") or []
    if not candidates:
        raise LLMError("Gemini provider returned no candidates.")
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    text = "".join(
        part.get("text", "") for part in parts if isinstance(part, dict)
    ).strip()
    if not text:
        raise LLMError("Gemini provider returned empty content.")
    return text


def _build_bedrock_payload(
    messages: list[dict[str, Any]],
    temperature: float | None,
) -> dict[str, Any]:
    system_text = _join_system_messages(messages)
    bedrock_messages: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        if role == "system":
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        mapped_role = "assistant" if role == "assistant" else "user"
        bedrock_messages.append(
            {"role": mapped_role, "content": [{"text": content}]}
        )
    payload: dict[str, Any] = {
        "messages": bedrock_messages,
        "inferenceConfig": {"temperature": 0 if temperature is None else temperature},
    }
    if system_text:
        payload["system"] = [{"text": system_text}]
    return payload


def _sign_bedrock_request(
    url: str,
    region: str,
    body: bytes,
    access_key: str,
    secret_key: str,
    session_token: str | None,
) -> dict[str, str]:
    if SigV4Auth is None or AWSRequest is None or Credentials is None:
        raise LLMError("botocore is required for Bedrock requests.")
    headers = {"Content-Type": "application/json"}
    request = AWSRequest(method="POST", url=url, data=body, headers=headers)
    credentials = Credentials(access_key, secret_key, session_token)
    SigV4Auth(credentials, "bedrock", region).add_auth(request)
    return dict(request.headers.items())


async def _call_bedrock(
    messages: list[dict[str, Any]],
    model_id: str,
    temperature: float | None,
) -> str:
    region = os.getenv("AWS_REGION", "").strip()
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    session_token = os.getenv("AWS_SESSION_TOKEN", "").strip() or None
    if not region or not access_key or not secret_key:
        raise LLMError("Missing AWS Bedrock credentials.")
    payload = _build_bedrock_payload(messages, temperature)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = (
        f"https://bedrock-runtime.{region}.amazonaws.com/"
        f"model/{model_id}/converse"
    )
    headers = _sign_bedrock_request(url, region, body, access_key, secret_key, session_token)
    response = await asyncio.to_thread(_http_post_body, url, body, headers)
    output = response.get("output") or {}
    message = output.get("message") or {}
    parts = message.get("content") or []
    text = "".join(
        part.get("text", "") for part in parts if isinstance(part, dict)
    ).strip()
    if not text:
        raise LLMError("Bedrock provider returned empty content.")
    return text


async def _call_provider(
    provider: str,
    task: str,
    messages: list[dict[str, Any]],
    temperature: float | None,
    response_format: str | None,
) -> LLMResult:
    provider = provider.lower()
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = _openai_model(task)
        base_url = _normalize_base_url(os.getenv("OPENAI_BASE_URL"))
        content = await _call_openai(
            messages, model, api_key, base_url, temperature, response_format
        )
        return LLMResult(content=content, provider="openai", model=model)
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        model = _deepseek_model(task)
        if not model:
            raise LLMError("DEEPSEEK_MODEL is required.")
        base_url = _normalize_base_url(os.getenv("DEEPSEEK_BASE_URL"))
        if not base_url:
            raise LLMError("DEEPSEEK_BASE_URL is required.")
        content = await _call_openai(
            messages, model, api_key, base_url, temperature, response_format
        )
        return LLMResult(content=content, provider="deepseek", model=model)
    if provider == "qwen":
        api_key = os.getenv("QWEN_API_KEY", "").strip()
        model = _qwen_model(task)
        if not model:
            raise LLMError("QWEN_MODEL is required.")
        base_url = _qwen_base_url()
        if not base_url:
            raise LLMError("QWEN_BASE_URL is required.")
        content = await _call_openai(
            messages, model, api_key, base_url, temperature, response_format
        )
        return LLMResult(content=content, provider="qwen", model=model)
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model = _gemini_model(task)
        if not model:
            raise LLMError("GEMINI_MODEL is required.")
        content = await _call_gemini(messages, model, api_key, temperature, response_format)
        return LLMResult(content=content, provider="gemini", model=model)
    if provider == "bedrock":
        model_id = _bedrock_model(task)
        if not model_id:
            raise LLMError("BEDROCK_MODEL_ID is required.")
        try:
            content = await _call_bedrock(messages, model_id, temperature)
            return LLMResult(content=content, provider="bedrock", model=model_id)
        except Exception:
            fallback = _bedrock_fallback_model()
            if fallback and fallback != model_id:
                content = await _call_bedrock(messages, fallback, temperature)
                return LLMResult(content=content, provider="bedrock", model=fallback)
            raise
    raise LLMError(f"Unsupported provider: {provider}")


async def _call_provider_stream(
    provider: str,
    task: str,
    messages: list[dict[str, Any]],
    temperature: float | None,
    response_format: str | None,
) -> LLMStream:
    provider = provider.lower()
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = _openai_model(task)
        base_url = _normalize_base_url(os.getenv("OPENAI_BASE_URL"))
        stream = await _call_openai_stream(
            messages, model, api_key, base_url, temperature, response_format
        )
        return LLMStream(provider="openai", model=model, stream=stream)
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        model = _deepseek_model(task)
        if not model:
            raise LLMError("DEEPSEEK_MODEL is required.")
        base_url = _normalize_base_url(os.getenv("DEEPSEEK_BASE_URL"))
        if not base_url:
            raise LLMError("DEEPSEEK_BASE_URL is required.")
        stream = await _call_openai_stream(
            messages, model, api_key, base_url, temperature, response_format
        )
        return LLMStream(provider="deepseek", model=model, stream=stream)
    if provider == "qwen":
        api_key = os.getenv("QWEN_API_KEY", "").strip()
        model = _qwen_model(task)
        if not model:
            raise LLMError("QWEN_MODEL is required.")
        base_url = _qwen_base_url()
        if not base_url:
            raise LLMError("QWEN_BASE_URL is required.")
        stream = await _call_openai_stream(
            messages, model, api_key, base_url, temperature, response_format
        )
        return LLMStream(provider="qwen", model=model, stream=stream)
    raise LLMError("Streaming is not supported for this provider.")


async def call_llm(
    task: str,
    messages: list[dict[str, Any]],
    temperature: float | None = None,
    response_format: str | None = None,
) -> LLMResult:
    providers = _resolve_provider_chain(task)
    if not providers:
        raise LLMError("No available LLM provider configured.")
    last_error: Exception | None = None
    for provider in providers:
        try:
            return await _call_provider(
                provider, task, messages, temperature, response_format
            )
        except Exception as exc:
            last_error = exc
            continue
    raise LLMError("All LLM providers failed.") from last_error


async def call_llm_stream(
    task: str,
    messages: list[dict[str, Any]],
    temperature: float | None = None,
    response_format: str | None = None,
) -> LLMStream:
    providers = _resolve_provider_chain(task)
    if not providers:
        raise LLMError("No available LLM provider configured.")
    last_error: Exception | None = None
    for provider in providers:
        if provider not in {"openai", "deepseek", "qwen"}:
            continue
        try:
            return await _call_provider_stream(
                provider, task, messages, temperature, response_format
            )
        except Exception as exc:
            last_error = exc
            continue
    raise LLMError("No streaming-capable LLM provider available.") from last_error
