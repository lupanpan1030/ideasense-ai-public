import re
from typing import Any

from app.services.chat_question_planning import question_schema_paths
from app.services.chat_market_type_normalization import (
    canonicalize_market_type_value,
    collect_strings,
    infer_market_type_enum_from_state,
)
from app.services.extraction_transforms import (
    get_nested_state_value,
    is_non_empty,
    split_state_path,
)

NONE_LIKE_TOKENS = {
    "none",
    "unknown",
    "n/a",
    "na",
    "no",
    "none/unknown",
    "unknown/none",
    "none or unknown",
    "no data",
    "not applicable",
    "无",
    "没有",
    "未知",
    "不确定",
    "无数据",
    "不适用",
}

COMPLIANCE_KEYWORDS = {
    "gdpr",
    "hipaa",
    "pci",
    "soc2",
    "soc 2",
    "sox",
    "ccpa",
    "ferpa",
    "finra",
    "sec",
    "fda",
    "medical",
    "health",
    "patient",
    "pharma",
    "clinical",
    "bank",
    "banking",
    "finance",
    "financial",
    "insurance",
    "government",
    "public sector",
    "k-12",
    "school",
    "student",
    "children",
    "child",
    "minor",
    "privacy",
    "compliance",
    "regulatory",
    "监管",
    "合规",
    "医疗",
    "健康",
    "患者",
    "金融",
    "银行",
    "保险",
    "政府",
    "学校",
    "学生",
    "儿童",
    "未成年",
    "隐私",
}

AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "ml",
    "machine learning",
    "llm",
    "gpt",
    "model",
    "embedding",
    "inference",
    "openai",
    "anthropic",
    "vertex",
    "bedrock",
    "huggingface",
    "fine-tune",
    "fine tune",
    "rag",
    "retrieval",
    "人工智能",
    "大模型",
    "模型",
    "机器学习",
    "算法",
    "生成式",
}

RELIABILITY_KEYWORDS = {
    "reliability",
    "uptime",
    "availability",
    "sla",
    "slo",
    "latency",
    "performance",
    "real-time",
    "realtime",
    "mission critical",
    "99.9",
    "99.99",
    "downtime",
    "outage",
    "稳定性",
    "可用性",
    "高可用",
    "低延迟",
    "延迟",
    "实时",
}

PATH_EQUIVALENTS = {
    "market_strategy.unit_economics.expected_payback_period_normalized": [
        "market_strategy.unit_economics.expected_payback_period_raw",
    ],
    "market_strategy.business_model.initial_price_point_normalized": [
        "market_strategy.business_model.initial_price_point_raw",
    ],
}


def is_required_question(type_raw: str | None) -> bool:
    if not isinstance(type_raw, str):
        return True
    return type_raw.strip().lower().startswith("required")


def is_optional_question(type_raw: str | None) -> bool:
    if not isinstance(type_raw, str):
        return False
    return type_raw.strip().lower().startswith("optional")


def is_conditional_question(type_raw: str | None) -> bool:
    if not isinstance(type_raw, str):
        return False
    return type_raw.strip().lower().startswith("conditional")


def normalize_market_type(value: Any) -> str | None:
    canonical = canonicalize_market_type_value(value)
    if not isinstance(canonical, str):
        return None
    normalized = canonical.strip().lower()
    if "hybrid" in normalized:
        return "hybrid"
    if "b2b" in normalized:
        return "b2b"
    if "b2c" in normalized:
        return "b2c"
    return None


def question_market_lock(question_detail: dict) -> str | None:
    title = str(question_detail.get("title") or "")
    prompt = str(question_detail.get("prompt") or "")
    haystack = f"{title} {prompt}".lower()
    if "b2b only" in haystack:
        return "b2b"
    if "b2c only" in haystack:
        return "b2c"
    return None


def is_meaningful_text(text: str) -> bool:
    cleaned = text.strip().lower()
    if not cleaned:
        return False
    if cleaned in NONE_LIKE_TOKENS:
        return False
    return True


def has_meaningful_value(value: Any) -> bool:
    for item in collect_strings(value):
        if is_meaningful_text(item):
            return True
    return False


def contains_keywords(value: Any, keywords: set[str]) -> bool:
    if not keywords:
        return False
    items = collect_strings(value)
    if not items:
        return False
    haystack = " ".join(item.strip().lower() for item in items if item and item.strip())
    if not haystack:
        return False
    for keyword in keywords:
        if not keyword:
            continue
        if len(keyword) <= 2:
            if re.search(rf"\b{re.escape(keyword)}\b", haystack):
                return True
            continue
        if keyword in haystack:
            return True
    return False


def is_compliance_triggered(state_json: Any) -> bool:
    if not isinstance(state_json, dict):
        return False
    data_types = get_nested_state_value(
        state_json, ["tech_execution", "security_compliance", "data_types"]
    )
    compliance_reqs = get_nested_state_value(
        state_json, ["tech_execution", "security_compliance", "compliance_requirements"]
    )
    if has_meaningful_value(data_types) or has_meaningful_value(compliance_reqs):
        return True
    return contains_keywords(state_json, COMPLIANCE_KEYWORDS)


def is_ai_data_triggered(state_json: Any) -> bool:
    if not isinstance(state_json, dict):
        return False
    if contains_keywords(
        get_nested_state_value(
            state_json, ["tech_execution", "data_ai_scalability", "ai_usage"]
        ),
        AI_KEYWORDS,
    ):
        return True
    if contains_keywords(
        get_nested_state_value(
            state_json, ["tech_execution", "dependencies", "key_integrations"]
        ),
        AI_KEYWORDS,
    ):
        return True
    if contains_keywords(
        get_nested_state_value(state_json, ["problem_user", "idea", "raw"]),
        AI_KEYWORDS,
    ):
        return True
    if contains_keywords(
        get_nested_state_value(state_json, ["market_strategy", "uvp", "one_line"]),
        AI_KEYWORDS,
    ):
        return True
    return contains_keywords(state_json, AI_KEYWORDS)


def is_high_reliability_triggered(state_json: Any) -> bool:
    if not isinstance(state_json, dict):
        return False
    if contains_keywords(
        get_nested_state_value(
            state_json, ["tech_execution", "product_scope", "non_functional_priorities"]
        ),
        RELIABILITY_KEYWORDS,
    ):
        return True
    if contains_keywords(
        get_nested_state_value(
            state_json,
            ["tech_execution", "data_ai_scalability", "performance_expectations"],
        ),
        RELIABILITY_KEYWORDS,
    ):
        return True
    if contains_keywords(
        get_nested_state_value(
            state_json, ["tech_execution", "roadmap_risks", "top_technical_risks"]
        ),
        RELIABILITY_KEYWORDS,
    ):
        return True
    return contains_keywords(state_json, RELIABILITY_KEYWORDS)


TRIGGER_CHECKS = {
    "compliance": is_compliance_triggered,
    "ai_data": is_ai_data_triggered,
    "high_reliability": is_high_reliability_triggered,
}


def question_triggers(question_detail: dict) -> list[str]:
    prompt_meta = question_detail.get("prompt_meta")
    if not isinstance(prompt_meta, dict):
        return []
    triggers = prompt_meta.get("triggers")
    if isinstance(triggers, str):
        return [triggers.strip().lower()] if triggers.strip() else []
    if isinstance(triggers, list):
        normalized: list[str] = []
        for item in triggers:
            if not isinstance(item, str):
                continue
            cleaned = item.strip().lower()
            if cleaned:
                normalized.append(cleaned)
        return normalized
    return []


def triggers_active(triggers: list[str], state_json: Any) -> bool:
    if not triggers:
        return True
    for trigger in triggers:
        checker = TRIGGER_CHECKS.get(trigger)
        if checker and checker(state_json):
            return True
    return False


def path_has_value(state_json: Any, path: str) -> bool:
    if not isinstance(state_json, dict):
        return False
    value = get_nested_state_value(state_json, split_state_path(path))
    return is_non_empty(value)


def filter_missing_paths_by_state(
    state_json: Any,
    missing_paths: list[str],
) -> list[str]:
    if not missing_paths or not isinstance(state_json, dict):
        return missing_paths
    filtered: list[str] = []
    for path in missing_paths:
        if path_has_value(state_json, path):
            continue
        equivalents = PATH_EQUIVALENTS.get(path, [])
        if equivalents and any(path_has_value(state_json, item) for item in equivalents):
            continue
        filtered.append(path)
    return filtered


def normalize_market_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        parts = [
            item.strip().lower()
            for item in value
            if isinstance(item, str) and item.strip()
        ]
        return " ".join(parts)
    return ""


def infer_market_type(state_json: Any) -> str | None:
    if not isinstance(state_json, dict):
        return None
    inferred_enum = infer_market_type_enum_from_state(state_json)
    if inferred_enum:
        return inferred_enum.strip().lower()
    inferred = normalize_market_type(
        get_nested_state_value(state_json, ["target_user", "market_type_inferred"])
    )
    if inferred:
        return inferred
    candidates = [
        normalize_market_text(
            get_nested_state_value(
                state_json, ["market_strategy", "meta", "market_type_override"]
            )
        ),
        normalize_market_text(
            get_nested_state_value(
                state_json, ["market_strategy", "business_model", "payer_role"]
            )
        ),
        normalize_market_text(
            get_nested_state_value(
                state_json, ["market_strategy", "business_model", "end_user_role"]
            )
        ),
    ]
    combined = " ".join([value for value in candidates if value])
    if not combined:
        return None
    has_b2b = (
        "b2b" in combined
        or "enterprise" in combined
        or "company" in combined
        or "team" in combined
    )
    has_b2c = (
        "b2c" in combined
        or "consumer" in combined
        or "individual" in combined
        or "founder" in combined
        or "indie" in combined
        or "prosumer" in combined
    )
    if "hybrid" in combined or (has_b2b and has_b2c):
        return "hybrid"
    if has_b2b:
        return "b2b"
    if has_b2c:
        return "b2c"
    return None


def should_skip_non_required_question(
    question_detail: dict,
    state_json: dict | None,
    missing_paths: list[str] | None,
) -> bool:
    type_raw = question_detail.get("type_raw")
    schema_paths = question_schema_paths(question_detail)
    if not schema_paths:
        return True

    if is_required_question(type_raw):
        if state_json and not filter_missing_paths_by_state(state_json, schema_paths):
            return True
        return False

    if is_optional_question(type_raw):
        if missing_paths is not None and not any(
            path in missing_paths for path in schema_paths
        ):
            return True
        return missing_paths is None

    if is_conditional_question(type_raw):
        triggers = question_triggers(question_detail)
        if triggers and not triggers_active(triggers, state_json):
            return True
        market_lock = question_market_lock(question_detail)
        if market_lock and state_json:
            inferred = infer_market_type(state_json)
            if inferred and inferred != market_lock:
                return True
        if state_json:
            missing = filter_missing_paths_by_state(state_json, schema_paths)
            if not missing:
                return True

    return False


def adjust_missing_paths_for_market(
    state_json: Any,
    missing_paths: list[str],
    resolved_paths: list[str] | None = None,
) -> list[str]:
    if not missing_paths or not isinstance(state_json, dict):
        return missing_paths
    expected_sales_path = "market_strategy.go_to_market.expected_sales_cycle_length"
    retention_path = "market_strategy.go_to_market.retention_loop"
    if expected_sales_path not in missing_paths and retention_path not in missing_paths:
        return missing_paths

    resolved = set(resolved_paths or [])
    has_retention = (
        is_non_empty(
            get_nested_state_value(
                state_json, ["market_strategy", "go_to_market", "retention_loop"]
            )
        )
        or retention_path in resolved
    )
    has_sales_cycle = (
        is_non_empty(
            get_nested_state_value(
                state_json,
                ["market_strategy", "go_to_market", "expected_sales_cycle_length"],
            )
        )
        or expected_sales_path in resolved
    )

    adjusted = list(missing_paths)
    if has_retention and expected_sales_path in adjusted:
        adjusted.remove(expected_sales_path)
    if has_sales_cycle and retention_path in adjusted:
        adjusted.remove(retention_path)

    if expected_sales_path in adjusted and retention_path in adjusted:
        market_type = infer_market_type(state_json)
        if market_type == "b2c" and expected_sales_path in adjusted:
            adjusted.remove(expected_sales_path)
        elif market_type == "b2b" and retention_path in adjusted:
            adjusted.remove(retention_path)

    return adjusted
