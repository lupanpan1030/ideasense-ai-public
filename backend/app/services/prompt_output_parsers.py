"""Registered output parsers for prompt runtime tasks."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal, Mapping, TypeVar, cast

from app.core.llm_parse_utils import parse_json_object
from pydantic import BaseModel, ValidationError, confloat


PromptOutputParser = Callable[[str], Any]
ModelT = TypeVar("ModelT", bound=BaseModel)


class AnswerGateScore(BaseModel):
    clarity: confloat(ge=0, le=1)
    completeness: confloat(ge=0, le=1)
    evidence: confloat(ge=0, le=1)


class AnswerGateResult(BaseModel):
    verdict: Literal["pass", "needs_info", "fail"]
    missing_points: list[str]
    critical_issues: list[str]
    followup_questions: list[str]
    help_examples: list[str]
    followup_message: str | None = None
    score: AnswerGateScore
    overall: confloat(ge=0, le=1)


class QuestionRewriteResult(BaseModel):
    prompt: str


def _validate_model(model_cls: type[ModelT], payload: Any) -> ModelT:
    validator = getattr(model_cls, "model_validate", None)
    if callable(validator):
        return validator(payload)
    return cast(ModelT, model_cls.parse_obj(payload))


def parse_answer_gate_payload(payload: str) -> AnswerGateResult | None:
    try:
        parsed = parse_json_object(payload)
    except Exception:
        return None
    try:
        return _validate_model(AnswerGateResult, parsed)
    except ValidationError:
        return None


def require_answer_gate_payload(payload: str) -> AnswerGateResult:
    parsed = parse_answer_gate_payload(payload)
    if parsed is None:
        raise ValueError("invalid answer gate payload")
    return parsed


def parse_question_rewrite_payload(payload: str) -> QuestionRewriteResult | None:
    try:
        parsed = parse_json_object(payload)
    except Exception:
        return None
    try:
        return _validate_model(QuestionRewriteResult, parsed)
    except ValidationError:
        return None


def require_question_rewrite_payload(payload: str) -> QuestionRewriteResult:
    parsed = parse_question_rewrite_payload(payload)
    if parsed is None:
        raise ValueError("invalid question rewrite payload")
    return parsed


def _to_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        if value != value:  # NaN check
            return None
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("score", "value", "total", "total_score"):
            if key in value:
                return _to_number(value.get(key))
    return None


def _normalize_decision_band(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"go", "hold", "stop"}:
        return text
    if text in {"green", "yes", "approve"}:
        return "go"
    if text in {"amber", "watch", "pivot"}:
        return "hold"
    if text in {"red", "no", "reject"}:
        return "stop"
    return None


def _pick_number(payload: Mapping[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        if key in payload:
            value = _to_number(payload.get(key))
            if value is not None:
                return value
    return None


def _normalize_scoreboard(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    desirability = _pick_number(raw, ["desirability", "desirability_score", "d"])
    viability = _pick_number(raw, ["viability", "viability_score", "v"])
    feasibility = _pick_number(raw, ["feasibility", "feasibility_score", "f"])
    total_score = _pick_number(raw, ["total_score", "total", "totalScore"])
    decision_band = _normalize_decision_band(
        raw.get("decision_band") or raw.get("decisionBand") or raw.get("decision")
    )
    if (
        desirability is None
        and viability is None
        and feasibility is None
        and total_score is None
        and decision_band is None
    ):
        return None
    return {
        "desirability": desirability,
        "viability": viability,
        "feasibility": feasibility,
        "total_score": total_score,
        "decision_band": decision_band,
    }


def _normalize_dimension(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    score = _to_number(raw.get("score") or raw.get("value"))
    comment = raw.get("comment") or raw.get("reason")
    comment_text = str(comment).strip() if isinstance(comment, str) else None
    subscores = raw.get("subscores") if isinstance(raw.get("subscores"), dict) else None
    confidence = _to_number(raw.get("confidence"))
    if score is None and not comment_text and not subscores and confidence is None:
        return None
    payload: dict[str, Any] = {
        "score": score,
        "comment": comment_text,
        "subscores": subscores,
    }
    if confidence is not None:
        payload["confidence"] = confidence
    return payload


def _normalize_assessment(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    desirability = _normalize_dimension(raw.get("desirability"))
    viability = _normalize_dimension(raw.get("viability"))
    feasibility = _normalize_dimension(raw.get("feasibility"))
    total_score = _pick_number(raw, ["total_score", "total", "totalScore"])
    if not any([desirability, viability, feasibility]) and total_score is None:
        return None
    return {
        "desirability": desirability,
        "viability": viability,
        "feasibility": feasibility,
        "total_score": total_score,
    }


def _assessment_from_scores(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    desirability = _normalize_dimension(raw.get("desirability"))
    viability = _normalize_dimension(raw.get("viability"))
    feasibility = _normalize_dimension(raw.get("feasibility"))
    total_score = _pick_number(raw, ["total", "total_score", "totalScore"])
    if not any([desirability, viability, feasibility]) and total_score is None:
        return None
    return {
        "desirability": desirability,
        "viability": viability,
        "feasibility": feasibility,
        "total_score": total_score,
    }


def _scoreboard_from_assessment(assessment: dict[str, Any]) -> dict[str, Any] | None:
    desirability = _pick_number(assessment, ["desirability"])
    if desirability is None and isinstance(assessment.get("desirability"), dict):
        desirability = _to_number(assessment["desirability"].get("score"))
    viability = _pick_number(assessment, ["viability"])
    if viability is None and isinstance(assessment.get("viability"), dict):
        viability = _to_number(assessment["viability"].get("score"))
    feasibility = _pick_number(assessment, ["feasibility"])
    if feasibility is None and isinstance(assessment.get("feasibility"), dict):
        feasibility = _to_number(assessment["feasibility"].get("score"))
    total_score = _pick_number(assessment, ["total_score", "total", "totalScore"])
    if total_score is None and None not in (desirability, viability, feasibility):
        total_score = round((desirability + viability + feasibility) / 3.0)
    if (
        desirability is None
        and viability is None
        and feasibility is None
        and total_score is None
    ):
        return None
    return {
        "desirability": desirability,
        "viability": viability,
        "feasibility": feasibility,
        "total_score": total_score,
        "decision_band": None,
    }


def _ensure_decision_band(scoreboard: dict[str, Any]) -> None:
    decision_band = _normalize_decision_band(scoreboard.get("decision_band"))
    total_score = _to_number(scoreboard.get("total_score"))
    if decision_band is None and total_score is not None:
        if total_score >= 70:
            decision_band = "go"
        elif total_score >= 40:
            decision_band = "hold"
        else:
            decision_band = "stop"
    scoreboard["decision_band"] = decision_band
    scoreboard["total_score"] = total_score


def normalize_dvf_payload(raw: dict[str, Any]) -> dict[str, Any] | None:
    scoreboard = _normalize_scoreboard(
        raw.get("dvf_scoreboard")
        or raw.get("dvfScoreboard")
        or raw.get("scoreboard")
    )
    assessment = _normalize_assessment(
        raw.get("dvf_assessment")
        or raw.get("dvfAssessment")
        or raw.get("assessment")
    )
    if assessment is None:
        assessment = _assessment_from_scores(raw.get("scores"))
    if scoreboard is None and assessment is not None:
        scoreboard = _scoreboard_from_assessment(assessment)
    if scoreboard is not None:
        if scoreboard.get("decision_band") is None and "decision_band" in raw:
            scoreboard["decision_band"] = raw.get("decision_band")
        if scoreboard.get("total_score") is None:
            total = _to_number(scoreboard.get("total_score"))
            if total is None and assessment is not None:
                total = _to_number(assessment.get("total_score"))
            if total is None:
                scores = [
                    _to_number(scoreboard.get("desirability")),
                    _to_number(scoreboard.get("viability")),
                    _to_number(scoreboard.get("feasibility")),
                ]
                if None not in scores:
                    total = round(sum(scores) / 3.0)
            scoreboard["total_score"] = total
        _ensure_decision_band(scoreboard)
    if assessment is not None and assessment.get("total_score") is None and scoreboard:
        assessment["total_score"] = scoreboard.get("total_score")

    key_risks = raw.get("key_risks") or raw.get("keyRisks")
    if not isinstance(key_risks, list):
        key_risks = []

    risk_matrix = raw.get("risk_matrix") or raw.get("riskMatrix")
    if isinstance(risk_matrix, list):
        risk_matrix = {"key_risks": risk_matrix}
    if not isinstance(risk_matrix, dict):
        risk_matrix = None

    payload: dict[str, Any] = {}
    if scoreboard is not None:
        payload["dvf_scoreboard"] = scoreboard
    if assessment is not None:
        payload["dvf_assessment"] = assessment
    if key_risks:
        payload["key_risks"] = key_risks
    if risk_matrix:
        payload["risk_matrix"] = risk_matrix

    return payload or None


def parse_dvf_payload(content: str) -> dict[str, Any]:
    parsed = parse_json_object(content)
    normalized = normalize_dvf_payload(parsed)
    if normalized is None:
        raise ValueError("invalid DVF scoring payload")
    return normalized


def parse_report_json_object(content: str) -> dict[str, Any] | None:
    try:
        return parse_json_object(content)
    except (json.JSONDecodeError, ValueError):
        return None


def normalize_report_sections(raw: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    scoreboard = raw.get("dvf_scoreboard") or raw.get("dvfScoreboard")
    if isinstance(scoreboard, dict):
        normalized["dvf_scoreboard"] = scoreboard

    assessment = raw.get("dvf_assessment") or raw.get("dvfAssessment")
    if isinstance(assessment, dict):
        normalized["dvf_assessment"] = assessment

    key_risks = raw.get("key_risks") or raw.get("keyRisks")
    if isinstance(key_risks, list):
        normalized["key_risks"] = key_risks

    risk_matrix = raw.get("risk_matrix") or raw.get("riskMatrix")
    if isinstance(risk_matrix, dict):
        normalized["risk_matrix"] = risk_matrix

    overall_summary = (
        raw.get("overall_summary")
        or raw.get("overallSummary")
        or raw.get("overall_report")
    )
    if isinstance(overall_summary, dict):
        overall_summary = (
            overall_summary.get("summary")
            or overall_summary.get("executive_summary")
            or overall_summary.get("executiveSummary")
        )
    if isinstance(overall_summary, str) and overall_summary.strip():
        normalized["overall_summary"] = overall_summary.strip()

    architecture_diagram = raw.get("architecture_diagram") or raw.get(
        "architectureDiagram"
    )
    if architecture_diagram is not None:
        normalized["architecture_diagram"] = architecture_diagram

    diagnosis = raw.get("diagnosis") or raw.get("diagnosis_summary") or raw.get(
        "diagnosisSummary"
    )
    if isinstance(diagnosis, dict):
        normalized["diagnosis"] = diagnosis
    elif isinstance(diagnosis, str) and diagnosis.strip():
        normalized["diagnosis"] = {"summary": diagnosis.strip()}

    validation_plan = (
        raw.get("validation_plan")
        or raw.get("next_validation_steps")
        or raw.get("validationPlan")
        or raw.get("nextValidationSteps")
    )
    if isinstance(validation_plan, list):
        normalized["validation_plan"] = validation_plan

    for source_key, normalized_key in (
        ("decision_snapshot", "decision_snapshot"),
        ("decisionSnapshot", "decision_snapshot"),
        ("score_rationales", "score_rationales"),
        ("scoreRationales", "score_rationales"),
        ("evidence_index", "evidence_index"),
        ("evidenceIndex", "evidence_index"),
    ):
        value = raw.get(source_key)
        if isinstance(value, dict):
            normalized[normalized_key] = value

    risk_register = raw.get("risk_register") or raw.get("riskRegister")
    if isinstance(risk_register, list):
        normalized["risk_register"] = risk_register

    experiment_plan = (
        raw.get("experiment_plan")
        or raw.get("experimentPlan")
        or raw.get("experiments")
    )
    if isinstance(experiment_plan, list):
        normalized["experiment_plan"] = experiment_plan

    artifact_schema_version = raw.get("artifact_schema_version") or raw.get(
        "artifactSchemaVersion"
    )
    if isinstance(artifact_schema_version, str) and artifact_schema_version.strip():
        normalized["artifact_schema_version"] = artifact_schema_version.strip()

    return normalized


def parse_final_report_payload(content: str) -> dict[str, Any]:
    parsed = parse_report_json_object(content)
    if not parsed:
        raise ValueError("invalid final report payload")
    normalized = normalize_report_sections(parsed)
    if not normalized:
        raise ValueError("empty final report payload")
    return normalized


PROMPT_OUTPUT_PARSERS: dict[str, PromptOutputParser] = {
    "answer_gate_json": require_answer_gate_payload,
    "schema_path_json": parse_json_object,
    "question_plan_json": parse_json_object,
    "question_rewrite_json": require_question_rewrite_payload,
    "claim_verification_json": parse_json_object,
    "dvf_json": parse_dvf_payload,
    "final_report_json": parse_final_report_payload,
}


def get_prompt_output_parser(parser_key: str | None) -> PromptOutputParser | None:
    if not parser_key or parser_key == "text":
        return None
    return PROMPT_OUTPUT_PARSERS.get(parser_key)


__all__ = [
    "AnswerGateResult",
    "AnswerGateScore",
    "PROMPT_OUTPUT_PARSERS",
    "PromptOutputParser",
    "QuestionRewriteResult",
    "get_prompt_output_parser",
    "normalize_dvf_payload",
    "normalize_report_sections",
    "parse_answer_gate_payload",
    "parse_dvf_payload",
    "parse_final_report_payload",
    "parse_question_rewrite_payload",
    "parse_report_json_object",
    "require_answer_gate_payload",
    "require_question_rewrite_payload",
]
