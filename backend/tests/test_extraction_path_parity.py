from app.services import answer_extraction_worker_handler as worker_extraction
from app.services import chat_sync_extraction_preview as sync_extraction


def _assert_extraction_path_parity(
    question_detail: dict,
    extracted: dict,
    answer: str,
    current_stage: str,
) -> None:
    sync_result = sync_extraction.prepare_extraction_updates(
        question_detail,
        extracted,
        current_stage,
        answer,
    )
    worker_result = worker_extraction._prepare_authoritative_extraction_updates(
        question_detail.get("schema_paths") or [],
        extracted,
        current_stage,
        answer,
    )

    assert worker_result == sync_result


def test_sync_preview_and_worker_match_for_product_scope_fallback() -> None:
    question_detail = {
        "question_id": "S3Q1",
        "schema_paths": [
            "market.uvp.one_line",
            "tech_execution.product_scope.current_status",
            "tech_execution.product_scope.mvp_definition",
            "tech_execution.product_scope.core_user_journeys",
            "tech_execution.product_scope.non_functional_priorities",
        ],
    }
    answer = (
        "A) Current status: working prototype.\n"
        "B) MVP boundaries: in MVP are project workspace and DVF report. "
        "Not in MVP are CRM and billing.\n"
        "C) Core journeys: 1) manager creates project; 2) mentor reviews context; "
        "3) team generates report.\n"
        "D) NFR priorities: security because of cohort data; latency because chat "
        "should feel responsive."
    )

    _assert_extraction_path_parity(
        question_detail,
        {"market": {"uvp": {"one_line": "Audit-ready founder reports."}}},
        answer,
        "tech",
    )


def test_sync_preview_and_worker_match_for_impact_fallback() -> None:
    _assert_extraction_path_parity(
        {
            "schema_paths": [
                "impact.time_impact",
                "impact.money_impact",
            ],
        },
        {},
        "Time wasted: 3 hours per week\nMoney impact: $500 lost revenue per month",
        "problem",
    )
