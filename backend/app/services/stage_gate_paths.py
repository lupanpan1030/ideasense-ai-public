from typing import Any

from app.services.answer_meta import get_answer_meta_map

PATH_EQUIVALENT_GROUPS: tuple[tuple[str, ...], ...] = (
    (
        "market_strategy.unit_economics.expected_payback_period_normalized",
        "market_strategy.unit_economics.expected_payback_period_raw",
    ),
    (
        "market_strategy.business_model.initial_price_point_normalized",
        "market_strategy.business_model.initial_price_point_raw",
    ),
    ("problem.scenarios", "problem.scenarios[]"),
    ("alternatives.current_solutions", "alternatives.current_solutions[]"),
    ("evidence.key_unknowns", "evidence.key_unknowns[]"),
    (
        "market_strategy.go_to_market.primary_channels",
        "market_strategy.go_to_market.primary_channels[]",
    ),
    (
        "market_strategy.validation.signals",
        "market_strategy.validation.signals[]",
    ),
    (
        "market_strategy.competition.competitor_types",
        "market_strategy.competition.competitor_types[]",
    ),
)

STAGE_BLOCKING_PATH_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    "problem": (
        ("problem.one_line",),
        ("target_user.core", "target_user.priority_segment"),
        ("problem.scenarios", "problem.scenarios[]"),
        ("alternatives.current_solutions", "alternatives.current_solutions[]"),
        ("evidence.key_unknowns", "evidence.key_unknowns[]"),
    ),
    "market": (
        ("market_strategy.uvp.one_line",),
        ("market_strategy.business_model.payer_role",),
        ("market_strategy.business_model.revenue_model",),
        (
            "market_strategy.competition.competitor_types",
            "market_strategy.competition.competitor_types[]",
        ),
        (
            "market_strategy.go_to_market.primary_channels",
            "market_strategy.go_to_market.primary_channels[]",
        ),
        (
            "market_strategy.validation.signals",
            "market_strategy.validation.signals[]",
        ),
    ),
    "tech": (
        ("tech_execution.product_scope.mvp_definition",),
        ("tech_execution.product_scope.core_user_journeys",),
        ("tech_execution.architecture.high_level_components",),
        ("tech_execution.data_ai_scalability.data_access_rights",),
        ("tech_execution.dependencies.key_integrations",),
        ("tech_execution.roadmap_risks.top_technical_risks",),
    ),
}


def _normalize_path(path: Any) -> str | None:
    if not isinstance(path, str):
        return None
    cleaned = path.strip()
    return cleaned if cleaned else None


def _normalize_stage(stage: Any) -> str | None:
    if not isinstance(stage, str):
        return None
    cleaned = stage.strip().lower()
    return cleaned if cleaned else None


def _normalize_variant(variant: Any) -> str | None:
    if not isinstance(variant, str):
        return None
    cleaned = variant.strip().lower()
    return cleaned if cleaned else None


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_is_non_empty(item) for item in value)
    if isinstance(value, dict):
        return any(_is_non_empty(item) for item in value.values())
    return True


def _get_value_by_path(state_json: Any, path: str) -> Any:
    cursor = state_json
    for raw_part in path.split("."):
        key = raw_part[:-2] if raw_part.endswith("[]") else raw_part
        if not isinstance(cursor, dict) or key not in cursor:
            return None
        cursor = cursor.get(key)
    return cursor


def _path_has_value(state_json: Any, path: str) -> bool:
    return _is_non_empty(_get_value_by_path(state_json, path))


def _expand_equivalent_paths(path: str) -> set[str]:
    expanded = {path}
    changed = True
    while changed:
        changed = False
        for group in PATH_EQUIVALENT_GROUPS:
            if expanded.intersection(group):
                next_size = len(expanded)
                expanded.update(group)
                if len(expanded) != next_size:
                    changed = True
    return expanded


def _unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw_path in paths:
        path = _normalize_path(raw_path)
        if path is None or path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def _group_is_resolved(
    group: tuple[str, ...],
    state_json: Any,
    answer_meta: dict[str, dict[str, Any]],
) -> bool:
    paths_to_check: set[str] = set()
    for path in group:
        paths_to_check.update(_expand_equivalent_paths(path))

    for path in paths_to_check:
        if _path_has_value(state_json, path):
            return True
        entry = answer_meta.get(path)
        if isinstance(entry, dict) and entry.get("resolution_status") == "not_applicable":
            return True
    return False


def get_stage_blocking_groups(stage: str | None) -> tuple[tuple[str, ...], ...]:
    normalized_stage = _normalize_stage(stage)
    if normalized_stage is None:
        return ()
    return STAGE_BLOCKING_PATH_GROUPS.get(normalized_stage, ())


def stage_allows_awaiting_confirm(
    stage: str | None,
    variant: str | None = None,
) -> bool:
    normalized_stage = _normalize_stage(stage)
    normalized_variant = _normalize_variant(variant)
    return not (
        normalized_stage == "tech" and normalized_variant == "router"
    )


def resolve_stage_blocking_paths(
    stage: str | None,
    available_paths: list[str] | None,
) -> list[str]:
    paths = _unique_paths(list(available_paths or []))
    if not paths:
        return []

    groups = get_stage_blocking_groups(stage)
    if not groups:
        return paths

    selected: list[str] = []
    matched_group = False
    for group in groups:
        present = [path for path in paths if path in group]
        if not present:
            continue
        matched_group = True
        for path in present:
            if path not in selected:
                selected.append(path)

    return selected if matched_group else paths


def filter_stage_blocking_missing_paths(
    stage: str | None,
    missing_paths: list[str] | None,
    *,
    state_json: Any,
    state_meta: Any = None,
) -> list[str]:
    paths = _unique_paths(list(missing_paths or []))
    if not paths:
        return []

    answer_meta = get_answer_meta_map(state_meta if isinstance(state_meta, dict) else {})
    groups = get_stage_blocking_groups(stage)

    if groups:
        group_by_path: dict[str, tuple[str, ...]] = {}
        has_configured_paths = False
        for group in groups:
            present = [path for path in paths if path in group]
            if not present:
                continue
            has_configured_paths = True
            for path in present:
                group_by_path[path] = group

        if has_configured_paths:
            unresolved_groups = {
                group
                for group in set(group_by_path.values())
                if not _group_is_resolved(group, state_json, answer_meta)
            }
            return [
                path
                for path in paths
                if group_by_path.get(path) in unresolved_groups
            ]

    filtered: list[str] = []
    for path in paths:
        if _group_is_resolved((path,), state_json, answer_meta):
            continue
        filtered.append(path)
    return filtered
