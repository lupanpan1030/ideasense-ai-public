import re
from copy import deepcopy
from typing import Any
from uuid import UUID

from app.core.llm_router import has_available_provider
from app.services.chat_ai_assist import AI_DRAFT_PREFIX
from app.services.chat_output_locale import (
    is_quick_action_answer,
    resolve_interview_output_locale,
)
from app.services.chat_question_filters import is_required_question
from app.services.chat_runtime_settings import (
    followup_compose_enabled,
    question_compose_enabled,
)
from app.services.chat_sync_extraction_preview import (
    should_soft_pass_answer,
)
from app.services.chat_sync_preview_question_matchers import (
    is_tech_mvp_boundary_prompt_question,
)
from app.services.extraction_transforms import has_explicit_none
from app.services.localization import (
    DEFAULT_OUTPUT_LOCALE,
    OutputLocale,
    output_language_label,
)
from app.services.prompt_output_parsers import AnswerGateResult
from app.services.prompt_runtime import (
    DEFAULT_PROMPT_TASK_REGISTRY,
    PromptContextBuilder,
    PromptMutationClass,
    prepare_prompt_task,
    render_prompt_messages,
)

QUESTION_COMPOSE_SOURCE = "llm_composed_question"
QUESTION_COMPOSE_FALLBACK_SOURCE = "question_engine_fallback"
FOLLOWUP_COMPOSE_SOURCE = "llm_composed_followup"
FOLLOWUP_COMPOSE_FALLBACK_SOURCE = "answer_gate_fallback"

CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
SPANISH_PATTERN = re.compile(r"[¿¡áéíóúñÁÉÍÓÚÑ]")
PROMPT_CONTEXT_BUILDER = PromptContextBuilder()


def normalize_list(value: Any) -> list[str]:
    if not value:
        return []
    if not isinstance(value, list):
        value = [value]
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                items.append(cleaned)
    return items


def is_internal_prompt_line(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if lowered.startswith(
        (
            "instruction:",
            "validation rule:",
            "standard question:",
            "schema paths:",
        )
    ):
        return True
    return cleaned.startswith(
        (
            "提示:",
            "提示：",
            "指示:",
            "指示：",
            "验证规则:",
            "验证规则：",
            "标准问题:",
            "标准问题：",
            "模式路径:",
            "模式路径：",
        )
    )


def sanitize_rewritten_prompt(text: str) -> str | None:
    if not isinstance(text, str):
        return None
    lines = text.splitlines()
    cleaned_lines: list[str] = []
    for line in lines:
        if is_internal_prompt_line(line):
            break
        cleaned_lines.append(line.rstrip())
    cleaned = "\n".join(cleaned_lines).strip()
    return cleaned or None


def sanitize_composed_question(text: str) -> str | None:
    if not isinstance(text, str):
        return None
    cleaned = text.strip()
    display_match = re.search(
        r"<DISPLAY>(.*?)</DISPLAY>",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if display_match:
        cleaned = display_match.group(1).strip()
    cleaned = re.sub(r"^```(?:markdown|md)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines()).strip()
    return cleaned or None


def is_language_mismatch(text: str, is_chinese: bool) -> bool:
    if not text.strip():
        return True
    if is_chinese:
        return not CJK_PATTERN.search(text)
    return bool(CJK_PATTERN.search(text) or SPANISH_PATTERN.search(text))


def select_fallback_followup(
    question_detail: dict,
    *,
    output_locale: OutputLocale = DEFAULT_OUTPUT_LOCALE,
) -> str:
    fallback = question_detail.get("standard_question") or question_detail.get("prompt")
    if isinstance(fallback, str) and fallback.strip():
        if output_locale == "zh" and CJK_PATTERN.search(fallback):
            return fallback.strip()
        if output_locale == "en" and not CJK_PATTERN.search(fallback):
            return fallback.strip()
    if output_locale == "zh":
        return "请补充当前问题里最关键、还没有说清楚的一点。"
    return "Please add the most critical missing detail."


def select_followup_answer_pattern(
    question_detail: dict,
    *,
    output_locale: OutputLocale = DEFAULT_OUTPUT_LOCALE,
) -> str:
    schema_paths = set(question_detail.get("schema_paths") or [])
    if is_tech_mvp_boundary_prompt_question(question_detail):
        if output_locale == "zh":
            return "当前状态：___；MVP 范围：___；不在 MVP 中：___。"
        return "Current status: ___; In-MVP scope: ___; Out-of-MVP boundary: ___."
    if {"impact.time_impact", "impact.money_impact"}.issubset(schema_paths):
        if output_locale == "zh":
            return (
                "时间影响：每周/每月 ___；金额影响：每月 ___（没有或未知也可以写明）。"
            )
        return "Time wasted: ___ per week/month; Money impact: ___ per month (or none/unknown)."
    if "problem.severity_score" in schema_paths:
        if output_locale == "zh":
            return "严重程度：__/10；原因：___。"
        return "Severity score: __/10; Reasons: ___."
    if "alternatives.current_solutions[]" in schema_paths:
        if output_locale == "zh":
            return "当前替代方案：___；满意度：__/10；主要抱怨：___。"
        return "Current solutions: ___; Satisfaction: __/10; Main complaints: ___."
    if "evidence.key_unknowns[]" in schema_paths:
        if output_locale == "zh":
            return "用户访谈：___ 次；关键学习：___；量化证据：___；待验证未知：___。"
        return "User conversations: ___; Key learnings: ___; Quant evidence: ___; Unknowns to de-risk: ___."
    if output_locale == "zh":
        return "第一版优先解决……，因为……。"
    return "The first version should prioritize ..., because ...."


def build_question_compose_context(
    question_detail: dict,
    base_prompt: str,
    latest_answer: str | None,
    context_summary: str | None,
    output_locale: OutputLocale,
) -> Any:
    return PROMPT_CONTEXT_BUILDER.question_compose(
        question_detail,
        base_prompt=base_prompt,
        latest_answer=latest_answer,
        context_summary=context_summary,
        output_language=output_language_label(output_locale),
    )


async def build_question_compose_prompt(
    session,
    question_detail: dict,
    base_prompt: str,
    latest_answer: str | None,
    context_summary: str | None,
    output_locale: OutputLocale,
    *,
    project_settings: dict | None = None,
) -> list[dict[str, str]]:
    context = build_question_compose_context(
        question_detail,
        base_prompt,
        latest_answer,
        context_summary,
        output_locale,
    )
    return await render_prompt_messages(
        session,
        context,
        project_settings=project_settings,
    )


def build_followup_compose_context(
    question_detail: dict,
    decision: dict,
    fallback_message: str,
    latest_answer: str | None,
    context_summary: str | None,
    output_locale: OutputLocale,
) -> Any:
    return PROMPT_CONTEXT_BUILDER.followup_compose(
        question_detail,
        decision,
        fallback_message=fallback_message,
        latest_answer=latest_answer,
        context_summary=context_summary,
        output_language=output_language_label(output_locale),
    )


async def build_followup_compose_prompt(
    session,
    question_detail: dict,
    decision: dict,
    fallback_message: str,
    latest_answer: str | None,
    context_summary: str | None,
    output_locale: OutputLocale,
    *,
    project_settings: dict | None = None,
) -> list[dict[str, str]]:
    context = build_followup_compose_context(
        question_detail,
        decision,
        fallback_message,
        latest_answer,
        context_summary,
        output_locale,
    )
    return await render_prompt_messages(
        session,
        context,
        project_settings=project_settings,
    )


def apply_repeated_followup_cap(
    decision: dict,
    question_detail: dict,
    answer: str,
    *,
    schema_paths: list[Any],
    resolved_paths: list[str],
    previous_answer_count: int,
) -> tuple[dict, list[str]]:
    if decision.get("final_verdict") == "pass":
        return decision, []
    if previous_answer_count < 1:
        return decision, []
    clean_answer = answer.strip() if isinstance(answer, str) else ""
    if not clean_answer:
        return decision, []

    schema_path_strings = [
        path.strip() for path in schema_paths if isinstance(path, str) and path.strip()
    ]
    if not schema_path_strings:
        return decision, []

    resolved_set = {path for path in resolved_paths if path in schema_path_strings}
    has_partial_fill = bool(resolved_set)
    has_user_unknown = has_explicit_none(clean_answer) or is_quick_action_answer(
        clean_answer
    )
    has_minimum_signal = len(clean_answer) >= 8
    if not has_partial_fill and not has_user_unknown and not has_minimum_signal:
        return decision, []

    unresolved_paths = [
        path for path in schema_path_strings if path not in resolved_set
    ]
    next_decision = {
        **decision,
        "final_verdict": "pass",
        "missing_points": [],
        "critical_issues": [],
        "followup_questions": [],
        "help_examples": [],
        "followup_message": None,
        "partial_advance": True,
        "partial_resolved_paths": sorted(resolved_set),
        "partial_unknown_paths": unresolved_paths,
    }
    risk_notes = [
        note
        for note in normalize_list(decision.get("risk_notes"))
        if note != "Answer lacks required specificity."
    ]
    risk_notes.append(
        "Repeated follow-up cap applied; unresolved fields are marked unknown."
    )
    next_decision["risk_notes"] = risk_notes
    return next_decision, unresolved_paths


def schema_path_display_label(path: str) -> str:
    cleaned = path.replace("[]", "")
    leaf = cleaned.split(".")[-1] if cleaned else path
    return leaf.replace("_", " ").strip() or path


def focus_followup_on_unresolved_paths(
    decision: dict,
    *,
    schema_paths: list[Any],
    resolved_paths: list[str],
) -> dict:
    schema_path_strings = [
        path.strip() for path in schema_paths if isinstance(path, str) and path.strip()
    ]
    if not schema_path_strings:
        return decision
    resolved_set = {path for path in resolved_paths if path in schema_path_strings}
    if not resolved_set:
        return decision
    unresolved_paths = [
        path for path in schema_path_strings if path not in resolved_set
    ]
    if not unresolved_paths:
        return decision

    labels = [schema_path_display_label(path) for path in unresolved_paths]
    fields = ", ".join(labels)
    next_decision = {
        **decision,
        "missing_points": [f"Missing fields: {fields}."],
        "followup_questions": [f"Please answer only the missing fields: {fields}."],
        "partial_resolved_paths": sorted(resolved_set),
        "partial_unresolved_paths": unresolved_paths,
    }
    risk_notes = normalize_list(decision.get("risk_notes"))
    risk_notes.append("Follow-up focused on unresolved fields after partial fill.")
    next_decision["risk_notes"] = risk_notes
    return next_decision


def build_gate_decision(
    question_detail: dict,
    answer: str,
    gate_result: AnswerGateResult | None,
    latest_answer: str | None = None,
) -> dict:
    unknown = False
    is_required = is_required_question(question_detail.get("type_raw"))
    threshold = 0.7 if is_required else 0.6
    model_verdict = gate_result.verdict if gate_result else "needs_info"
    completeness = float(gate_result.score.completeness) if gate_result else 0.0
    overall = float(gate_result.overall) if gate_result else 0.0
    final_verdict = model_verdict
    if gate_result is None or unknown:
        final_verdict = "needs_info"
    elif model_verdict == "pass":
        final_verdict = "pass"
    elif completeness < threshold or overall < threshold:
        final_verdict = "needs_info"

    missing_points = normalize_list(gate_result.missing_points if gate_result else None)
    critical_issues = normalize_list(
        gate_result.critical_issues if gate_result else None
    )
    followup_questions = normalize_list(
        gate_result.followup_questions if gate_result else None
    )
    help_examples = normalize_list(gate_result.help_examples if gate_result else None)
    followup_message = (
        gate_result.followup_message.strip()
        if gate_result
        and isinstance(gate_result.followup_message, str)
        and gate_result.followup_message.strip()
        else None
    )

    validation_rule = question_detail.get("validation_rule")
    if (
        final_verdict != "pass"
        and not missing_points
        and isinstance(validation_rule, str)
    ):
        cleaned_rule = validation_rule.strip()
        if cleaned_rule:
            missing_points = [cleaned_rule]

    standard_question = question_detail.get("standard_question")
    if (
        final_verdict != "pass"
        and not followup_questions
        and isinstance(standard_question, str)
    ):
        cleaned_standard = standard_question.strip()
        if cleaned_standard:
            followup_questions = [cleaned_standard]

    risk_notes: list[str] = []
    if unknown:
        risk_notes.append(
            "User indicated unknown; needs assumptions and a validation plan."
        )
    if final_verdict != "pass" and not risk_notes:
        risk_notes.append("Answer lacks required specificity.")

    if final_verdict != "pass" and not unknown:
        soft_pass = should_soft_pass_answer(question_detail, answer, gate_result)
        if (
            not soft_pass
            and isinstance(latest_answer, str)
            and latest_answer.strip()
            and latest_answer.strip() != answer.strip()
        ):
            soft_pass = should_soft_pass_answer(
                question_detail,
                latest_answer,
                gate_result,
            )
        if soft_pass:
            final_verdict = "pass"
            missing_points = []
            critical_issues = []
            followup_questions = []
            help_examples = []
            risk_notes = [
                note
                for note in risk_notes
                if note != "Answer lacks required specificity."
            ]
            risk_notes.append("Soft pass applied based on heuristic validation.")

    score_payload = {
        "clarity": float(gate_result.score.clarity) if gate_result else 0.0,
        "completeness": completeness,
        "evidence": float(gate_result.score.evidence) if gate_result else 0.0,
    }

    return {
        "final_verdict": final_verdict,
        "model_verdict": model_verdict,
        "missing_points": missing_points,
        "critical_issues": critical_issues,
        "followup_questions": followup_questions,
        "help_examples": help_examples,
        "followup_message": followup_message,
        "risk_notes": risk_notes,
        "score": score_payload,
        "overall": overall,
        "unknown": unknown,
        "threshold": threshold,
    }


async def build_question_stream_context(
    session,
    *,
    project_id: str,
    org_id: str,
    stage: str | None,
    variant: str | None,
    question_instance_id: UUID,
    question_detail: dict,
    fallback_content: str,
    meta: dict[str, Any],
    output_locale: OutputLocale,
    latest_answer: str | None,
    context_summary: str | None,
    message_meta: Any | None = None,
    project_settings: dict | None = None,
    answer_evaluation_request_id: str | None = None,
) -> dict[str, Any]:
    compose_messages = None
    compose_timeout_ms = None
    compose_trace = None
    compose_prepare_failure = None
    compose_prepared = None
    question_output_locale = resolve_interview_output_locale(
        latest_answer,
        output_locale,
        context_summary=context_summary,
        message_meta=message_meta,
    )
    resolved_meta = deepcopy(meta)
    resolved_meta["content_locale"] = question_output_locale
    if question_output_locale != output_locale:
        resolved_meta["requested_output_locale"] = output_locale
        resolved_meta["locale_source"] = "latest_user_answer"
    compose_task = DEFAULT_PROMPT_TASK_REGISTRY.get("question_compose")
    if question_compose_enabled() and fallback_content.strip():
        compose_context = build_question_compose_context(
            question_detail,
            fallback_content,
            latest_answer,
            context_summary,
            question_output_locale,
        )
        prepared = await prepare_prompt_task(
            session,
            compose_context,
            project_settings=project_settings,
            expected_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
            provider_check=has_available_provider,
        )
        compose_trace = dict(prepared.trace)
        if prepared.ok:
            compose_messages = prepared.messages
            compose_timeout_ms = prepared.timeout_ms
            compose_prepared = prepared
        elif prepared.failure:
            compose_prepare_failure = prepared.failure.reason
    return {
        "project_id": project_id,
        "org_id": org_id,
        "stage": stage,
        "variant": variant,
        "question_instance_id": question_instance_id,
        "question_detail": deepcopy(question_detail),
        "fallback_content": fallback_content,
        "meta": resolved_meta,
        "compose_prepared": compose_prepared,
        "compose_task_key": compose_task.task_key,
        "compose_messages": compose_messages,
        "compose_task": compose_task.provider_task,
        "compose_temperature": compose_task.temperature,
        "compose_response_format": compose_task.response_format,
        "compose_timeout_ms": compose_timeout_ms,
        "compose_trace": compose_trace,
        "compose_prepare_failure": compose_prepare_failure,
        "success_source": QUESTION_COMPOSE_SOURCE,
        "fallback_source": QUESTION_COMPOSE_FALLBACK_SOURCE,
        "answer_evaluation_request_id": answer_evaluation_request_id,
        "output_locale": question_output_locale,
        "requested_output_locale": output_locale,
    }


async def build_followup_stream_context(
    session,
    *,
    project_id: str,
    org_id: str,
    stage: str | None,
    variant: str | None,
    question_instance_id: UUID,
    question_detail: dict,
    decision: dict,
    fallback_content: str,
    meta: dict[str, Any],
    output_locale: OutputLocale,
    latest_answer: str | None,
    context_summary: str | None,
    message_meta: Any | None = None,
    project_settings: dict | None = None,
    answer_evaluation_request_id: str | None = None,
) -> dict[str, Any]:
    compose_messages = None
    compose_timeout_ms = None
    compose_trace = None
    compose_prepare_failure = None
    compose_prepared = None
    followup_output_locale = resolve_interview_output_locale(
        latest_answer,
        output_locale,
        context_summary=context_summary,
        message_meta=message_meta,
    )
    resolved_meta = deepcopy(meta)
    resolved_meta["content_locale"] = followup_output_locale
    if followup_output_locale != output_locale:
        resolved_meta["requested_output_locale"] = output_locale
        resolved_meta["locale_source"] = "latest_user_answer"
    compose_task = DEFAULT_PROMPT_TASK_REGISTRY.get("followup_compose")
    if followup_compose_enabled() and fallback_content.strip():
        compose_context = build_followup_compose_context(
            question_detail,
            decision,
            fallback_content,
            latest_answer,
            context_summary,
            followup_output_locale,
        )
        prepared = await prepare_prompt_task(
            session,
            compose_context,
            project_settings=project_settings,
            expected_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
            provider_check=has_available_provider,
        )
        compose_trace = dict(prepared.trace)
        if prepared.ok:
            compose_messages = prepared.messages
            compose_timeout_ms = prepared.timeout_ms
            compose_prepared = prepared
        elif prepared.failure:
            compose_prepare_failure = prepared.failure.reason
    return {
        "project_id": project_id,
        "org_id": org_id,
        "stage": stage,
        "variant": variant,
        "question_instance_id": question_instance_id,
        "question_detail": deepcopy(question_detail),
        "fallback_content": fallback_content,
        "meta": resolved_meta,
        "compose_prepared": compose_prepared,
        "compose_task_key": compose_task.task_key,
        "compose_messages": compose_messages,
        "compose_task": compose_task.provider_task,
        "compose_temperature": compose_task.temperature,
        "compose_response_format": compose_task.response_format,
        "compose_timeout_ms": compose_timeout_ms,
        "compose_trace": compose_trace,
        "compose_prepare_failure": compose_prepare_failure,
        "success_source": FOLLOWUP_COMPOSE_SOURCE,
        "fallback_source": FOLLOWUP_COMPOSE_FALLBACK_SOURCE,
        "answer_evaluation_request_id": answer_evaluation_request_id,
        "output_locale": followup_output_locale,
        "requested_output_locale": output_locale,
    }


def build_followup_message(
    question_detail: dict,
    decision: dict,
    latest_answer: str | None = None,
    *,
    output_locale: OutputLocale = DEFAULT_OUTPUT_LOCALE,
) -> str:
    followup_message = decision.get("followup_message")

    missing_points = decision.get("missing_points") or []
    critical_issues = decision.get("critical_issues") or []
    followups = decision.get("followup_questions") or []
    examples = decision.get("help_examples") or []

    missing_points = [
        item
        for item in missing_points
        if isinstance(item, str)
        and not is_language_mismatch(item, output_locale == "zh")
    ]
    critical_issues = [
        item
        for item in critical_issues
        if isinstance(item, str)
        and not is_language_mismatch(item, output_locale == "zh")
    ]
    followups = [
        item
        for item in followups
        if isinstance(item, str)
        and not is_language_mismatch(item, output_locale == "zh")
    ]
    examples = [
        item
        for item in examples
        if isinstance(item, str)
        and not is_language_mismatch(item, output_locale == "zh")
    ]

    validation_rule = question_detail.get("validation_rule")
    if (
        isinstance(validation_rule, str)
        and validation_rule.strip()
        and len(missing_points) == 1
        and missing_points[0].strip() == validation_rule.strip()
    ):
        missing_points = []

    items: list[str] = []
    if followups:
        items.extend(
            [item for item in followups if isinstance(item, str) and item.strip()]
        )
    if not items and missing_points:
        if output_locale == "zh":
            items.extend([f"请补充/说明清楚：{item}" for item in missing_points])
        else:
            items.extend([f"Please add/clarify: {item}" for item in missing_points])
    if critical_issues:
        if output_locale == "zh":
            items.extend([f"请修正：{item}" for item in critical_issues])
        else:
            items.extend([f"Please fix: {item}" for item in critical_issues])
    if (
        not items
        and output_locale == "en"
        and isinstance(followup_message, str)
        and followup_message.strip()
    ):
        items.append(followup_message.strip())

    if not items:
        items.append(
            select_fallback_followup(
                question_detail,
                output_locale=output_locale,
            )
        )

    items = [item for item in items if isinstance(item, str) and item.strip()]
    if len(items) > 3:
        items = items[:3]

    if output_locale == "zh":
        intro = "我理解你已经给了一部分信息。为了继续往下一步走，还需要补充："
    else:
        intro = (
            "Thanks — I got most of it. A few quick clarifications so we can move on:"
        )
    lines: list[str] = [intro]
    if items:
        lines.extend([f"- {item}" for item in items])

    if examples:
        lines.append("示例：" if output_locale == "zh" else "Example:")
        lines.append(f"- {examples[0]}")

    if output_locale == "zh":
        lines.append("可以直接按这个句式回答：")
    else:
        lines.append("You can answer in this format:")
    lines.append(
        select_followup_answer_pattern(
            question_detail,
            output_locale=output_locale,
        )
    )

    if decision.get("unknown"):
        if output_locale == "zh":
            lines.append(
                "如果还不确定，请给一个具体假设和验证计划（谁/验证什么/什么时候）。"
            )
            lines.append(f"需要草稿的话，可以回复「{AI_DRAFT_PREFIX}」或「AI draft」。")
        else:
            lines.append(
                "If you're unsure, give a concrete assumption and a validation plan (who/what/when)."
            )
            lines.append(f"Need a draft? Reply with '{AI_DRAFT_PREFIX}' or 'AI draft'.")

    return "\n".join(lines).strip()
