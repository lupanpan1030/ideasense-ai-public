from app.services.verification.claim_selection import _extract_claims_from_summaries


def test_extract_claims_from_summaries_skips_legacy_ai_assisted_aliases() -> None:
    claims = _extract_claims_from_summaries(
        {
            "problem": "\n".join(
                [
                    "- [AI-assisted] Drafted market assumption",
                    "- [ai补全] Legacy localized marker",
                    "- Clear user-validated problem statement",
                ]
            )
        }
    )

    assert claims == [
        {
            "text": "Clear user-validated problem statement",
            "section": "problem",
        }
    ]
