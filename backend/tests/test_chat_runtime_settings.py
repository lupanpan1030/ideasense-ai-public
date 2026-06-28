from unittest.mock import patch

from app.services.chat_runtime_settings import (
    followup_compose_enabled,
    parse_csv_set,
    parse_env_flag,
    question_compose_enabled,
    resolve_question_compose_start_timeout_sec,
    resolve_question_group_settings,
    resolve_question_planner_settings,
)


def test_parse_env_flag_uses_defaults_and_false_values() -> None:
    with patch.dict("os.environ", {}, clear=True):
        assert parse_env_flag("MISSING_FLAG", True) is True
        assert parse_env_flag("MISSING_FLAG", False) is False

    for value in ("0", "false", "False", "no", "off", " OFF "):
        with patch.dict("os.environ", {"FEATURE_FLAG": value}, clear=True):
            assert parse_env_flag("FEATURE_FLAG", True) is False

    with patch.dict("os.environ", {"FEATURE_FLAG": "yes"}, clear=True):
        assert parse_env_flag("FEATURE_FLAG", False) is True


def test_parse_csv_set_trims_and_lowercases_values() -> None:
    assert parse_csv_set(" problem, Market ,, TECH ") == {"problem", "market", "tech"}
    assert parse_csv_set(None) == set()
    assert parse_csv_set("") == set()


def test_resolve_question_group_settings_applies_bounds_and_single_question_disable() -> None:
    with patch.dict(
        "os.environ",
        {
            "QUESTION_GROUP_ENABLED": "1",
            "QUESTION_TRANSITION_ENABLED": "0",
            "QUESTION_GROUP_MAX": "1",
        },
        clear=True,
    ):
        assert resolve_question_group_settings() == (False, 1, False)

    with patch.dict("os.environ", {"QUESTION_GROUP_MAX": "-2"}, clear=True):
        assert resolve_question_group_settings() == (False, 1, True)


def test_resolve_question_planner_settings_applies_defaults_and_lower_bounds() -> None:
    with patch.dict(
        "os.environ",
        {
            "QUESTION_PLANNER_ENABLED": "false",
            "QUESTION_PLANNER_MAX_QUESTIONS": "0",
            "QUESTION_PLANNER_MAX_SCHEMA": "0",
            "QUESTION_PLANNER_TIMEOUT_MS": "100",
            "QUESTION_PLANNER_CANDIDATE_LIMIT": "0",
            "QUESTION_PLANNER_MIN_MISSING_PATHS": "0",
            "QUESTION_PLANNER_MIN_CANDIDATES": "0",
            "QUESTION_PLANNER_STAGES": "problem, TECH",
        },
        clear=True,
    ):
        settings = resolve_question_planner_settings()

    assert settings == {
        "enabled": False,
        "max_questions": 1,
        "max_schema": 1,
        "timeout_ms": 200,
        "candidate_limit": 1,
        "min_missing_paths": 1,
        "min_candidates": 1,
        "stages": {"problem", "tech"},
    }


def test_compose_toggles_use_expected_defaults_and_flags() -> None:
    with patch.dict("os.environ", {}, clear=True):
        assert question_compose_enabled() is True
        assert followup_compose_enabled() is True

    with patch.dict(
        "os.environ",
        {
            "QUESTION_COMPOSE_ENABLED": "0",
            "FOLLOWUP_COMPOSE_ENABLED": "off",
        },
        clear=True,
    ):
        assert question_compose_enabled() is False
        assert followup_compose_enabled() is False


def test_resolve_question_compose_start_timeout_sec_uses_explicit_and_registry_timeout() -> None:
    assert resolve_question_compose_start_timeout_sec(2500) == 2.5
    assert resolve_question_compose_start_timeout_sec(-5) == 0

    with patch(
        "app.services.chat_runtime_settings.resolve_prompt_task_timeout_ms",
        return_value=1250,
    ):
        assert resolve_question_compose_start_timeout_sec() == 1.25

    with patch(
        "app.services.chat_runtime_settings.resolve_prompt_task_timeout_ms",
        return_value=None,
    ):
        assert resolve_question_compose_start_timeout_sec() == 3.5
