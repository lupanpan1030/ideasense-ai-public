from typing import Any

from app.services.chat_ai_assist import requires_single_sentence
from app.services.extraction_transforms import get_nested_state_value


def collect_key_points(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    points: list[str] = []
    seen: set[str] = set()

    def add_value(value: Any) -> None:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                points.append(cleaned)
            return
        if isinstance(value, (int, float, bool)):
            cleaned = str(value).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                points.append(cleaned)
            return
        if isinstance(value, list):
            for item in value:
                add_value(item)

    for value in payload.values():
        add_value(value)
    return points


def build_assistant_meta(
    *,
    base_meta: dict[str, Any] | None = None,
    decision: dict | None = None,
    rolling_summary: str | None = None,
    key_points: list[str] | None = None,
    question_meta: dict[str, Any] | None = None,
    content_locale: str | None = None,
) -> dict[str, Any]:
    meta = dict(base_meta or {})
    if decision is not None:
        meta["decision"] = decision
    if isinstance(rolling_summary, str) and rolling_summary.strip():
        meta["rolling_summary"] = rolling_summary
    if key_points:
        meta["key_points"] = key_points
    if question_meta:
        meta["question_meta"] = question_meta
    if isinstance(content_locale, str) and content_locale.strip():
        meta["content_locale"] = content_locale.strip().lower()
    return meta


def select_gate_answer(
    question_detail: dict,
    latest_answer: str,
    combined_answer: str,
) -> str:
    if requires_single_sentence(question_detail):
        if isinstance(latest_answer, str) and latest_answer.strip():
            return latest_answer
    return combined_answer


def select_extraction_answer(
    question_detail: dict,
    latest_answer: str,
    combined_answer: str,
) -> str:
    if requires_single_sentence(question_detail):
        if isinstance(latest_answer, str) and latest_answer.strip():
            return latest_answer
    return combined_answer


def normalize_context_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else None
    if isinstance(value, list):
        items = [
            item.strip() for item in value if isinstance(item, str) and item.strip()
        ]
        if not items:
            return None
        return "; ".join(items)
    return None


def truncate_context_value(value: str, max_length: int = 240) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def build_gate_context_summary(
    state_json: Any,
    runtime_stage: str | None,
    question_detail: dict,
    latest_answer: str,
) -> str | None:
    if not isinstance(state_json, dict):
        return None

    unknown_label = "Unknown"

    labels = {
        "p0_user": "Priority user",
        "problem": "MVP priority problem",
        "uvp": "UVP",
        "segment": "Initial segment",
        "positioning": "Competition positioning",
        "header": "Context summary",
    }

    values: list[tuple[str, str | None]] = [
        (
            labels["p0_user"],
            normalize_context_value(
                get_nested_state_value(state_json, ["target_user", "core"])
            ),
        ),
        (
            labels["problem"],
            normalize_context_value(
                get_nested_state_value(state_json, ["problem", "one_line"])
            ),
        ),
        (
            labels["uvp"],
            normalize_context_value(
                get_nested_state_value(
                    state_json, ["market_strategy", "uvp", "one_line"]
                )
            ),
        ),
    ]

    if runtime_stage and runtime_stage.lower() == "market":
        values.extend(
            [
                (
                    labels["segment"],
                    normalize_context_value(
                        get_nested_state_value(
                            state_json,
                            [
                                "market_strategy",
                                "market_size",
                                "initial_segment_definition",
                            ],
                        )
                    ),
                ),
                (
                    labels["positioning"],
                    normalize_context_value(
                        get_nested_state_value(
                            state_json,
                            ["market_strategy", "competition", "positioning_summary"],
                        )
                    ),
                ),
            ]
        )

    has_any = any(value for _, value in values)
    if not has_any:
        return None

    lines: list[str] = [f"{labels['header']}:"]
    for label, value in values:
        rendered = value or unknown_label
        lines.append(f"{label}: {truncate_context_value(rendered)}")
    return "\n".join(lines)
