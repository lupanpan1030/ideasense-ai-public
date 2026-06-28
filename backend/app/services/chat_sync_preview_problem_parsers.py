from __future__ import annotations

import re

from app.services.extraction_text_heuristics import (
    _strip_list_prefix,
    _extract_labeled_answer_value,
    _extract_labeled_impact_value,
    _extract_money_impact_value,
    _extract_time_impact_value,
    _has_money_impact_answer,
    _has_time_impact_answer,
)
from app.services.extraction_transforms import (
    has_explicit_none as _has_explicit_none,
    is_non_empty as _is_non_empty,
)


HISTORY_REFERENCE_PATTERNS = [
    re.compile(
        r"^(同上|如上|见上|如前|同前|如前所述|同上所述|参考上文|参考之前|沿用之前|沿用上文|同之前|同上面|如前面)[。.!]*$"
    ),
    re.compile(
        r"^(same as above|as above|see above|same as before|refer to previous|ditto|same as earlier)[.!]*$",
        re.IGNORECASE,
    ),
]


def looks_like_history_reference(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return True
    return any(pattern.search(cleaned) for pattern in HISTORY_REFERENCE_PATTERNS)


def _extract_primary_line(answer: str) -> str | None:
    for raw_line in answer.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.search(r"(?:^|\\s)#?1[\\).:\\s]", line) or line.startswith("1."):
            cleaned = re.sub(r"^[^a-zA-Z0-9]*#?1[\\).:\\s-]+", "", line).strip()
            return cleaned if cleaned else line
        stripped = _strip_list_prefix(line)
        if not stripped:
            continue
        for pattern in (
            r"(?:most important|top priority|mvp priority|mvp)(?: problem)?(?: is|:)?\\s*(.+)$",
            r"(?:最重要|首要|核心|重点|优先级最高|MVP\\s*重点|MVP\\s*优先)(?:的)?(?:问题)?(?:是|：|:)?\\s*(.+)$",
        ):
            match = re.search(pattern, stripped, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if candidate:
                    return candidate
        if re.search(
            r"(?:most important|top priority|mvp|priority|最重要|首要|核心|重点|优先|MVP\\s*重点)",
            stripped,
            flags=re.IGNORECASE,
        ):
            return stripped
    return None


def _looks_like_idea_snapshot_answer(answer: str) -> bool:
    cleaned = " ".join(answer.strip().split())
    if len(cleaned) < 40:
        return False
    if _has_explicit_none(cleaned):
        return False
    return bool(re.search(r"[A-Za-z\u4e00-\u9fff]", cleaned))


def _looks_like_top_problems_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    marker = re.search(r"(?m)^\\s*(?:[#＃]\\s*)?1(?:[\\).、:\\-]|\\s)", cleaned)
    if marker or re.search(r"[#＃]1", cleaned):
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if re.match(r"^(?:[#＃]?1(?:[\\).、:\\-]|\\s))", line):
                body = re.sub(r"^(?:[#＃]?1(?:[\\).、:\\-]|\\s)+)", "", line).strip()
                if body:
                    return True
        return len(cleaned) >= 20

    priority_marker = re.search(
        r"(?:most important|top priority|mvp|priority|最重要|首要|核心|重点|优先|MVP\\s*重点)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not priority_marker:
        return False

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    has_list_marker = any(
        re.match(r"^(?:[-*]|\\d+[\\).、]|[#＃]?\\d+[\\).、])\\s+", line)
        for line in lines
    )
    has_multi = len(lines) >= 2 or any(sep in cleaned for sep in (";", "；", "、"))
    return has_list_marker or has_multi or len(cleaned) >= 30


def _extract_score_out_of_ten(answer: str, labels: tuple[str, ...]) -> int | None:
    label_pattern = "|".join(labels)
    labeled = re.search(
        rf"(?:{label_pattern})\s*[:：-]?\s*(10|[1-9])(?:\s*(?:/|out\s+of)\s*10)?\b",
        answer,
        flags=re.IGNORECASE,
    )
    if labeled:
        return int(labeled.group(1))
    generic = re.search(
        r"\b(10|[1-9])\s*(?:/|out\s+of)\s*10\b",
        answer,
        flags=re.IGNORECASE,
    )
    if generic:
        return int(generic.group(1))
    return None


def _extract_severity_score(answer: str) -> int | None:
    return _extract_score_out_of_ten(
        answer,
        (
            r"severity\s*score",
            r"severity",
            r"pain(?:ful)?\s*score",
            r"urgency\s*score",
            r"score",
        ),
    )


def _extract_severity_reason(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"reason(?:s)?",
            r"reason\s*\d+",
            r"why",
        ),
    )
    if labeled:
        return labeled
    reason_lines = [
        line.strip()
        for line in answer.splitlines()
        if re.match(r"^(?:[-*]\s*)?reason\s*\d+\s*[:：-]", line.strip(), re.IGNORECASE)
    ]
    if reason_lines:
        return " ".join(reason_lines)
    cleaned = re.sub(
        r"(?:severity\s*score|severity|score)\s*[:：-]?\s*(?:10|[1-9])(?:\s*(?:/|out\s+of)\s*10)?[.。]?",
        "",
        answer,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned if len(cleaned) >= 20 else None


def _has_severity_answer(answer: str) -> bool:
    return _extract_severity_score(answer) is not None and _is_non_empty(
        _extract_severity_reason(answer)
    )


def _extract_current_solutions_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"current\s*solutions",
            r"solutions?",
            r"tools(?:/process(?:es)?/workarounds)?",
            r"workarounds?",
        ),
    )


def _extract_satisfaction_score(answer: str) -> int | None:
    return _extract_score_out_of_ten(
        answer,
        (
            r"satisfaction\s*score",
            r"satisfaction",
            r"rate",
            r"rating",
        ),
    )


def _extract_main_complaints_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"main\s*complaints",
            r"top\s*(?:2-3\s*)?complaints",
            r"complaints",
            r"gaps?",
        ),
    )


def _has_alternatives_answer(answer: str) -> bool:
    return (
        _is_non_empty(_extract_current_solutions_value(answer))
        and _extract_satisfaction_score(answer) is not None
        and _is_non_empty(_extract_main_complaints_value(answer))
    )


def _extract_user_interview_count_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"user\s*conversations",
            r"user\s*interviews?",
            r"interview\s*count",
            r"conversation\s*count",
        ),
    )


def _extract_key_learnings_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"key\s*learnings?",
            r"learnings?",
            r"insights?",
        ),
    )


def _extract_data_evidence_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"quant(?:itative)?\s*evidence(?:/proxies)?",
            r"evidence/proxies",
            r"evidence\s*proxies",
            r"data\s*evidence",
            r"proxies",
        ),
    )


def _extract_key_unknowns_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"key\s*unknowns?",
            r"top\s*(?:1-2\s*)?unknowns?",
            r"unknowns?\s*to\s*de-?risk",
            r"unknowns?",
        ),
    )


def _has_evidence_validation_answer(answer: str) -> bool:
    return (
        _is_non_empty(_extract_user_interview_count_value(answer))
        and _is_non_empty(_extract_key_learnings_value(answer))
        and _is_non_empty(_extract_data_evidence_value(answer))
        and _is_non_empty(_extract_key_unknowns_value(answer))
    )


def _has_problem_scenarios_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if (
        len(cleaned) < 40
        or _has_explicit_none(cleaned)
        or looks_like_history_reference(cleaned)
    ):
        return False
    if re.search(
        r"\b(?:unknown|unsure|not sure|don't know|do not know)\b",
        cleaned,
        re.IGNORECASE,
    ):
        return False
    scenario_markers = len(
        re.findall(
            r"\b(?:scenario|situation|case|example)\s*\d*\b",
            cleaned,
            re.IGNORECASE,
        )
    )
    context_markers = sum(
        1
        for pattern in (
            r"\bwhen\b",
            r"\bbefore\b",
            r"\bafter\b",
            r"\bduring\b",
            r"\bresult(?:s|ing)?\b",
            r"\blead(?:s|ing)?\b",
            r"\bhappen(?:s)?\b",
        )
        if re.search(pattern, cleaned, flags=re.IGNORECASE)
    )
    return scenario_markers >= 1 or context_markers >= 2
