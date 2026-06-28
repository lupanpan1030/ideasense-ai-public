from app.services.extraction_transforms import (
    build_extraction_targets,
    canonicalize_extraction_update_value,
    get_nested_state_value,
    has_explicit_none,
    is_non_empty,
    remap_extracted,
    split_state_path,
)


def _canonicalize_for_test(path: str, value):
    if path == "market_strategy.meta.market_type_override":
        return "B2B"
    return value


def test_remap_extracted_maps_nested_suffixes_and_list_paths() -> None:
    remapped = remap_extracted(
        {
            "target_user": {"core": "student founders"},
            "current_solutions": "spreadsheets",
            "market_strategy": {
                "meta": {"market_type_override": "business teams"}
            },
        },
        [
            "target_user.core",
            "alternatives.current_solutions[]",
            "market_strategy.meta.market_type_override",
        ],
        canonicalize_value=_canonicalize_for_test,
    )

    assert remapped == {
        "target_user.core": "student founders",
        "alternatives.current_solutions[]": ["spreadsheets"],
        "market_strategy.meta.market_type_override": "B2B",
    }


def test_remap_extracted_skips_ambiguous_suffixes() -> None:
    remapped = remap_extracted(
        {"value": "ambiguous"},
        ["problem.value", "market.value"],
    )

    assert remapped == {}


def test_has_explicit_none_detects_user_unknowns() -> None:
    assert has_explicit_none("No data yet")
    assert has_explicit_none("暂无")
    assert not has_explicit_none("")
    assert not has_explicit_none("We interviewed five teams")


def test_is_non_empty_handles_nested_containers() -> None:
    assert not is_non_empty({"items": ["", None, {}]})
    assert is_non_empty({"items": ["", {"answer": "yes"}]})
    assert is_non_empty(False)
    assert not is_non_empty("")


def test_canonicalize_extraction_update_value_preserves_explicit_meta() -> None:
    value = canonicalize_extraction_update_value(
        "market_strategy.meta.market_type_override",
        {
            "value": "business teams",
            "resolution_status": "partial",
            "claim_type": "estimate",
            "source": "llm",
            "ignored": "not copied",
        },
        canonicalize_value=_canonicalize_for_test,
    )

    assert value == {
        "value": "B2B",
        "resolution_status": "partial",
        "claim_type": "estimate",
        "source": "llm",
    }


def test_build_extraction_targets_assigns_state_and_pending_targets() -> None:
    resolved_paths, updates = build_extraction_targets(
        {
            "problem.one_line": "Manual reporting is slow.",
            "market.uvp.one_line": {"value": "Close faster.", "source": "ai"},
            "problem.empty": "",
        },
        "problem",
        canonicalize_value=_canonicalize_for_test,
    )

    assert resolved_paths == ["problem.one_line", "market.uvp.one_line"]
    assert updates == [
        ("state", "problem.one_line", "Manual reporting is slow."),
        ("pending", "market.uvp.one_line", {"value": "Close faster.", "source": "ai"}),
    ]


def test_nested_state_path_helpers_strip_array_suffixes() -> None:
    state_json = {"a": {"b": {"c": 3}}}

    assert split_state_path("a.b[].c") == ["a", "b", "c"]
    assert get_nested_state_value(state_json, ["a", "b", "c"]) == 3
    assert get_nested_state_value(state_json, ["a", "missing"]) is None
