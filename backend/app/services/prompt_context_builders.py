"""Sectioned prompt context assembly helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.services.prompt_runtime import PromptContext, PromptSection


def _normalize_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, tuple):
        value = list(value)
    elif not isinstance(value, list):
        value = [value]
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                items.append(cleaned)
    return items


def _format_list(value: Any, *, empty: str) -> str:
    items = _normalize_list(value)
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def _format_answer_gate_expected_points(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    return "\n".join(
        f"- {point}"
        for point in value
        if isinstance(point, str) and point.strip()
    )


def _truncate_text(text: str | None, limit: int = 800) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def _bounded_text(
    text: str | None,
    limit: int,
    *,
    empty: str,
) -> tuple[str, bool]:
    cleaned = (text or "").strip()
    rendered = _truncate_text(text, limit)
    return rendered or empty, bool(cleaned and len(cleaned) > limit)


def _serialize_payload(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True)


class PromptContextBuilder:
    def question_plan(
        self,
        *,
        stage: str | None,
        variant: str | None,
        missing_paths: list[str],
        latest_answer: str | None,
        candidate_list: str,
        max_questions: int,
        max_schema: int,
        output_language: str,
    ) -> PromptContext:
        missing_paths_list = (
            "\n".join(f"- {path}" for path in missing_paths)
            if missing_paths
            else "None"
        )
        latest_answer_text = _truncate_text(latest_answer) or ""
        variables = {
            "stage": stage,
            "variant": variant,
            "missing_paths_list": missing_paths_list,
            "latest_answer": latest_answer_text,
            "candidate_list": candidate_list,
            "max_questions": max_questions,
            "max_schema": max_schema,
            "output_language": output_language,
        }
        return PromptContext(
            task_key="question_plan",
            variables=variables,
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection("missing_paths", missing_paths_list, required=True),
                PromptSection(
                    "latest_answer",
                    latest_answer_text,
                    required=False,
                    budget_chars=800,
                    truncated=bool(latest_answer and len(latest_answer.strip()) > 800),
                ),
                PromptSection("candidate_questions", candidate_list, required=True),
                PromptSection(
                    "planner_limits",
                    f"max_questions={max_questions}; max_schema={max_schema}",
                    required=True,
                ),
            ),
        )

    def question_rewrite(
        self,
        task_key: str,
        question_detail: Mapping[str, Any],
        *,
        output_language: str,
    ) -> PromptContext:
        schema_list = _format_list(question_detail.get("schema_paths"), empty="None")
        variables = {
            "question_id": question_detail.get("question_id"),
            "stage": question_detail.get("stage"),
            "variant": question_detail.get("variant"),
            "type_raw": question_detail.get("type_raw"),
            "output_language": output_language,
            "prompt": question_detail.get("prompt"),
            "instruction": question_detail.get("instruction"),
            "validation_rule": question_detail.get("validation_rule"),
            "standard_question": question_detail.get("standard_question"),
            "schema_list": schema_list,
        }
        return PromptContext(
            task_key=task_key,
            variables=variables,
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection(
                    "selected_question",
                    str(question_detail.get("prompt") or ""),
                    required=True,
                ),
                PromptSection(
                    "stage_question_contract",
                    "\n".join(
                        str(variables.get(key) or "")
                        for key in (
                            "question_id",
                            "stage",
                            "variant",
                            "type_raw",
                            "instruction",
                            "validation_rule",
                            "standard_question",
                        )
                    ),
                    required=True,
                ),
                PromptSection("schema_paths", schema_list, required=True),
            ),
        )

    def answer_gate(
        self,
        question_detail: Mapping[str, Any],
        answer: str,
        context_summary: str | None = None,
    ) -> PromptContext:
        schema_list = _format_list(question_detail.get("schema_paths"), empty="")
        expected_points = _format_answer_gate_expected_points(
            question_detail.get("expected_key_points")
        )
        context_block = f"{context_summary}\n\n" if context_summary else ""
        variables = {
            "question_id": question_detail.get("question_id"),
            "stage": question_detail.get("stage"),
            "variant": question_detail.get("variant"),
            "type_raw": question_detail.get("type_raw"),
            "prompt": question_detail.get("prompt"),
            "validation_rule": question_detail.get("validation_rule"),
            "instruction": question_detail.get("instruction"),
            "expected_key_points": expected_points,
            "schema_list": schema_list,
            "context_block": context_block,
            "answer": answer,
        }
        return PromptContext(
            task_key="answer_gate",
            variables=variables,
            sections=(
                PromptSection(
                    "stage_question_contract",
                    "\n".join(
                        str(variables.get(key) or "")
                        for key in (
                            "question_id",
                            "stage",
                            "variant",
                            "type_raw",
                            "prompt",
                            "validation_rule",
                            "instruction",
                        )
                    ),
                    required=True,
                ),
                PromptSection(
                    "expected_key_points",
                    expected_points,
                    required=False,
                ),
                PromptSection("schema_paths", schema_list, required=True),
                PromptSection(
                    "project_context",
                    context_summary or "",
                    required=False,
                ),
                PromptSection("latest_answer", answer, required=True),
            ),
        )

    def extraction(self, schema_paths: list[str], user_text: str) -> PromptContext:
        schema_list = "\n".join(f"- {path}" for path in schema_paths)
        return PromptContext(
            task_key="extract",
            variables={
                "schema_list": schema_list,
                "user_text": user_text,
            },
            sections=(
                PromptSection("schema_paths", schema_list, required=True),
                PromptSection("latest_answer", user_text, required=True),
            ),
        )

    def question_compose(
        self,
        question_detail: Mapping[str, Any],
        *,
        base_prompt: str,
        latest_answer: str | None,
        context_summary: str | None,
        output_language: str,
    ) -> PromptContext:
        latest_answer_text, latest_truncated = _bounded_text(
            latest_answer,
            1000,
            empty="None",
        )
        context_summary_text, context_truncated = _bounded_text(
            context_summary,
            1400,
            empty="None",
        )
        expected_key_points = _format_list(
            question_detail.get("expected_key_points"),
            empty="None",
        )
        schema_list = _format_list(question_detail.get("schema_paths"), empty="None")
        variables = {
            "question_id": question_detail.get("question_id"),
            "stage": question_detail.get("stage"),
            "variant": question_detail.get("variant"),
            "output_language": output_language,
            "latest_answer": latest_answer_text,
            "context_summary": context_summary_text,
            "prompt": base_prompt,
            "instruction": question_detail.get("instruction") or "None",
            "validation_rule": question_detail.get("validation_rule") or "None",
            "expected_key_points": expected_key_points,
            "schema_list": schema_list,
        }
        return PromptContext(
            task_key="question_compose",
            variables=variables,
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection(
                    "latest_answer",
                    latest_answer_text,
                    required=True,
                    budget_chars=1000,
                    truncated=latest_truncated,
                ),
                PromptSection(
                    "project_context",
                    context_summary_text,
                    required=False,
                    budget_chars=1400,
                    truncated=context_truncated,
                ),
                PromptSection("selected_question", base_prompt, required=True),
                PromptSection(
                    "stage_question_contract",
                    "\n".join(
                        str(variables.get(key) or "")
                        for key in (
                            "question_id",
                            "stage",
                            "variant",
                            "instruction",
                            "validation_rule",
                        )
                    ),
                    required=True,
                ),
                PromptSection(
                    "expected_key_points",
                    expected_key_points,
                    required=False,
                ),
                PromptSection("schema_paths", schema_list, required=True),
            ),
        )

    def followup_compose(
        self,
        question_detail: Mapping[str, Any],
        decision: Mapping[str, Any],
        *,
        fallback_message: str,
        latest_answer: str | None,
        context_summary: str | None,
        output_language: str,
    ) -> PromptContext:
        latest_answer_text, latest_truncated = _bounded_text(
            latest_answer,
            1000,
            empty="None",
        )
        context_summary_text, context_truncated = _bounded_text(
            context_summary,
            1400,
            empty="None",
        )
        missing_points = _format_list(decision.get("missing_points"), empty="None")
        critical_issues = _format_list(decision.get("critical_issues"), empty="None")
        followup_questions = _format_list(
            decision.get("followup_questions"),
            empty="None",
        )
        help_examples = _format_list(decision.get("help_examples"), empty="None")
        expected_key_points = _format_list(
            question_detail.get("expected_key_points"),
            empty="None",
        )
        schema_list = _format_list(question_detail.get("schema_paths"), empty="None")
        variables = {
            "question_id": question_detail.get("question_id"),
            "stage": question_detail.get("stage"),
            "variant": question_detail.get("variant"),
            "output_language": output_language,
            "prompt": question_detail.get("prompt") or "None",
            "latest_answer": latest_answer_text,
            "context_summary": context_summary_text,
            "fallback_message": fallback_message or "None",
            "missing_points": missing_points,
            "critical_issues": critical_issues,
            "followup_questions": followup_questions,
            "help_examples": help_examples,
            "instruction": question_detail.get("instruction") or "None",
            "validation_rule": question_detail.get("validation_rule") or "None",
            "expected_key_points": expected_key_points,
            "schema_list": schema_list,
        }
        return PromptContext(
            task_key="followup_compose",
            variables=variables,
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection("selected_question", variables["prompt"], required=True),
                PromptSection(
                    "latest_answer",
                    latest_answer_text,
                    required=True,
                    budget_chars=1000,
                    truncated=latest_truncated,
                ),
                PromptSection(
                    "project_context",
                    context_summary_text,
                    required=False,
                    budget_chars=1400,
                    truncated=context_truncated,
                ),
                PromptSection(
                    "gate_decision",
                    "\n".join(
                        (
                            missing_points,
                            critical_issues,
                            followup_questions,
                            help_examples,
                        )
                    ),
                    required=True,
                ),
                PromptSection(
                    "backend_fallback",
                    fallback_message or "None",
                    required=True,
                ),
                PromptSection(
                    "stage_question_contract",
                    "\n".join(
                        str(variables.get(key) or "")
                        for key in (
                            "question_id",
                            "stage",
                            "variant",
                            "instruction",
                            "validation_rule",
                        )
                    ),
                    required=True,
                ),
                PromptSection(
                    "expected_key_points",
                    expected_key_points,
                    required=False,
                ),
                PromptSection("schema_paths", schema_list, required=True),
            ),
        )

    def ai_assist(
        self,
        question_detail: Mapping[str, Any],
        *,
        context_summary: str | None,
        sentence_hint: str,
        output_language: str,
    ) -> PromptContext:
        context_block = f"{context_summary}\n\n" if context_summary else ""
        variables = {
            "output_language": output_language,
            "prompt": question_detail.get("prompt"),
            "validation_rule": question_detail.get("validation_rule"),
            "instruction": question_detail.get("instruction"),
            "context_block": context_block,
            "sentence_hint": sentence_hint,
        }
        return PromptContext(
            task_key="ai_assist",
            variables=variables,
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection(
                    "selected_question",
                    str(question_detail.get("prompt") or ""),
                    required=True,
                ),
                PromptSection(
                    "stage_question_contract",
                    "\n".join(
                        str(variables.get(key) or "")
                        for key in ("validation_rule", "instruction")
                    ),
                    required=False,
                ),
                PromptSection(
                    "project_context",
                    context_summary or "",
                    required=False,
                ),
                PromptSection("output_constraints", sentence_hint, required=True),
            ),
        )

    def qa_digest(
        self,
        *,
        question_id: str,
        key_points: list[str],
        rolling_summary: str | None,
        output_language: str,
    ) -> PromptContext:
        payload_json = _serialize_payload(
            {
                "question_id": question_id,
                "key_points": key_points,
                "rolling_summary": rolling_summary,
            }
        )
        return PromptContext(
            task_key="qa_digest",
            variables={
                "output_language": output_language,
                "payload_json": payload_json,
            },
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection("qa_digest_input", payload_json, required=True),
            ),
        )

    def stage_summary(
        self,
        stage: str,
        payload: Mapping[str, Any],
        *,
        output_language: str,
    ) -> PromptContext:
        stage_key = stage.strip().lower()
        if stage_key not in {"problem", "market", "tech"}:
            raise ValueError(f"Unsupported stage for summary: {stage}")
        payload_json = _serialize_payload(payload)
        return PromptContext(
            task_key=f"stage_summary_{stage_key}",
            variables={
                "output_language": output_language,
                "stage": stage,
                "payload_json": payload_json,
            },
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection("report_input", payload_json, required=True),
            ),
        )

    def project_description(
        self,
        *,
        title: str | None,
        payload: Mapping[str, Any],
        summary: str | None,
        output_language: str,
    ) -> PromptContext:
        payload_json = _serialize_payload(payload)
        return PromptContext(
            task_key="project_description",
            variables={
                "output_language": output_language,
                "title": title or "",
                "summary": summary or "",
                "payload_json": payload_json,
            },
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection("project_title", title or "", required=False),
                PromptSection("stage_summary", summary or "", required=False),
                PromptSection("report_input", payload_json, required=True),
            ),
        )

    def dvf_scoring(
        self,
        payload: Mapping[str, Any],
        *,
        output_language: str,
    ) -> PromptContext:
        payload_json = _serialize_payload(payload)
        return PromptContext(
            task_key="dvf_scoring",
            variables={
                "output_language": output_language,
                "payload_json": payload_json,
            },
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection("report_input", payload_json, required=True),
                PromptSection(
                    "output_constraints",
                    "dvf_scoreboard, dvf_assessment, key_risks, risk_matrix",
                    required=True,
                ),
            ),
        )

    def final_report(
        self,
        report_input: Mapping[str, Any],
        *,
        output_language: str,
    ) -> PromptContext:
        payload_json = _serialize_payload(report_input)
        return PromptContext(
            task_key="final_report",
            variables={
                "output_language": output_language,
                "payload_json": payload_json,
            },
            sections=(
                PromptSection("output_locale", output_language, required=True),
                PromptSection("report_input", payload_json, required=True),
                PromptSection(
                    "output_constraints",
                    (
                        "overall_summary, diagnosis_summary, "
                        "next_validation_steps"
                    ),
                    required=True,
                ),
            ),
        )

    def claim_verification(
        self,
        *,
        claim: str,
        evidence: list[dict[str, Any]],
    ) -> PromptContext:
        payload_json = _serialize_payload(
            {
                "claim": claim,
                "evidence": evidence,
            }
        )
        return PromptContext(
            task_key="claim_verification",
            variables={"payload_json": payload_json},
            sections=(
                PromptSection("verification_input", payload_json, required=True),
            ),
        )
