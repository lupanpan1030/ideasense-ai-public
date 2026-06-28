from app.services.chat_turn_commit_shapers import (
    build_needs_info_assistant_meta,
    build_next_question_assistant_meta,
    build_router_mode_state_event_patch,
    build_skip_answer_status_meta,
    build_stage_gate_ready_payload,
    build_stage_transition_assistant_meta,
    build_state_event_patch,
    derive_updated_runtime_missing_paths,
    normalize_project_state_payload,
    resolve_routing_state_json,
    resolve_standard_question_routing,
    should_update_chat_state_meta,
)


def test_should_update_chat_state_meta_detects_patch_sources() -> None:
    assert not should_update_chat_state_meta(
        extraction_updates=[],
        skip_requested=False,
        schema_paths=[],
        partial_unknown_paths=[],
    )
    assert should_update_chat_state_meta(
        extraction_updates=[("state", "problem.one_line", "Pain")],
        skip_requested=False,
        schema_paths=[],
        partial_unknown_paths=[],
    )
    assert should_update_chat_state_meta(
        extraction_updates=[],
        skip_requested=True,
        schema_paths=["problem.one_line"],
        partial_unknown_paths=[],
    )
    assert should_update_chat_state_meta(
        extraction_updates=[],
        skip_requested=False,
        schema_paths=[],
        partial_unknown_paths=["problem.one_line"],
    )


def test_normalize_project_state_payload_defends_against_non_dict_values() -> None:
    payload = normalize_project_state_payload(
        {
            "state_json": None,
            "state_meta": {"pending_confirm": "bad"},
            "state_version": None,
        }
    )

    assert payload.state_json == {}
    assert payload.state_meta == {"pending_confirm": "bad"}
    assert payload.pending_confirm == {}
    assert payload.state_version == 0
    assert payload.has_existing_state is True


def test_build_state_event_patch_preserves_commit_payload_keys() -> None:
    patch = build_state_event_patch(
        runtime_stage="problem",
        runtime_variant="default",
        resolved_paths=["problem.one_line"],
        extraction_updates=[
            ("state", "problem.one_line", "Scheduling pain"),
            ("pending", "market.size", "Large"),
        ],
        skip_requested=True,
        partial_unknown_paths=["problem.frequency"],
    )

    assert patch == {
        "source": "chat_sync_extraction",
        "stage": "problem",
        "variant": "default",
        "resolved_paths": ["problem.one_line"],
        "state_paths": ["problem.one_line"],
        "pending_paths": ["market.size"],
        "skip_requested": True,
        "partial_unknown_paths": ["problem.frequency"],
    }


def test_build_skip_answer_status_meta_preserves_commit_keys() -> None:
    meta = build_skip_answer_status_meta(
        answer_action=None,
        skip_resolution_status="accepted",
        skip_reason="user skipped",
    )

    assert meta == {
        "skip_mode": "soft",
        "answer_action": "skip_soft",
        "resolution_status": "accepted",
        "skip_reason": "user skipped",
    }


def test_build_router_mode_state_event_patch_preserves_commit_keys() -> None:
    patch = build_router_mode_state_event_patch(mode="pro")

    assert patch == {
        "source": "router_mode_selection",
        "stage": "tech",
        "variant": "router",
        "state_paths": ["tech_execution.meta.mode"],
        "mode": "pro",
    }


def test_build_stage_gate_ready_payload_includes_context_metadata() -> None:
    payload = build_stage_gate_ready_payload(
        gate_context={"project_id": "project-1"},
        stage="problem",
        context_version=5,
        context_updated_at="2026-01-01T00:00:00Z",
    )

    assert payload == {
        "project_id": "project-1",
        "stage": "problem",
        "next_stage": "market",
        "stage_status": "awaiting_confirm",
        "context_version": 5,
        "context_updated_at": "2026-01-01T00:00:00Z",
    }


def test_resolve_routing_state_json_prefers_current_state_then_gate_context() -> None:
    assert resolve_routing_state_json(
        state_json={"current": True},
        gate_context={"state_json": {"fallback": True}},
    ) == {"current": True}

    assert resolve_routing_state_json(
        state_json=None,
        gate_context={"state_json": {"fallback": True}},
    ) == {"fallback": True}

    assert resolve_routing_state_json(
        state_json=None,
        gate_context={"state_json": "bad"},
    ) is None


def test_derive_updated_runtime_missing_paths_removes_resolved_paths() -> None:
    result = derive_updated_runtime_missing_paths(
        runtime_stage="problem",
        runtime_variant="default",
        runtime_missing_paths=["problem.one_line", "problem.frequency"],
        resolved_paths=["problem.one_line"],
        skip_requested=False,
        state_json={},
        state_meta={},
    )

    assert result.updated_missing_paths == ["problem.frequency"]
    assert result.changed is True


def test_resolve_standard_question_routing_enters_stage_gate_review() -> None:
    result = resolve_standard_question_routing(
        gate_context={"stage_status": "in_progress"},
        runtime_stage="problem",
        runtime_variant="default",
        next_question_id="next-question",
        updated_missing_paths=[],
        stage_status_ready="awaiting_confirm",
    )

    assert result.stage_gate_ready_for_review is True
    assert result.next_question_id is None
    assert result.updated_missing_paths == []


def test_build_next_question_assistant_meta_keeps_locale_and_group_payload() -> None:
    meta = build_next_question_assistant_meta(
        gate_context={"output_locale": "zh"},
        question_detail={"question_id": "q1", "schema_paths": ["problem.one_line"]},
        decision={"final_verdict": "accept"},
        rolling_summary="Summary",
        key_points=["Point"],
        group_meta_payload={"question_ids": ["q1", "q2"]},
        planned_question_prompt="计划问题",
        planner_used=False,
    )

    assert meta["schema_version"] == "v1"
    assert meta["question_id"] == "q1"
    assert meta["content_locale"] == "zh"
    assert meta["question_group"] == {"question_ids": ["q1", "q2"]}
    assert meta["decision"] == {"final_verdict": "accept"}


def test_build_needs_info_assistant_meta_preserves_question_payload() -> None:
    payload = build_needs_info_assistant_meta(
        gate_context={
            "output_locale": "zh",
            "question_detail": {
                "question_id": "q-needs-info",
                "stage": "problem",
                "variant": "default",
                "prompt_meta": {"ui": {"input": "textarea"}},
            },
        },
        decision={"final_verdict": "needs_info"},
        rolling_summary="Summary",
        key_points=["Point"],
    )

    assert payload.question_meta_payload == {
        "question_id": "q-needs-info",
        "stage": "problem",
        "variant": "default",
        "ui": {"input": "textarea"},
    }
    assert payload.assistant_meta["schema_version"] == "v1"
    assert payload.assistant_meta["question_id"] == "q-needs-info"
    assert payload.assistant_meta["content_locale"] == "zh"
    assert payload.assistant_meta["decision"] == {"final_verdict": "needs_info"}
    assert payload.assistant_meta["question_meta"] == payload.question_meta_payload


def test_build_stage_transition_assistant_meta_has_no_question_payload() -> None:
    meta = build_stage_transition_assistant_meta(
        gate_context={"output_locale": "en"},
        decision={"final_verdict": "accept"},
        rolling_summary=None,
        key_points=[],
    )

    assert meta["schema_version"] == "v1"
    assert meta["content_locale"] == "en"
    assert meta["decision"] == {"final_verdict": "accept"}
    assert "question_id" not in meta
    assert "question_meta" not in meta
