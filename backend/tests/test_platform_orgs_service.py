import asyncio
import unittest
from datetime import datetime, timezone
from uuid import UUID

from app.services.platform_orgs import (
    PlatformOrgNotFoundError,
    PlatformOrgValidationError,
    build_platform_org_filters,
    fetch_platform_orgs_payload,
    row_to_platform_org_payload,
    update_platform_org_payload,
)


ORG_ID = UUID("33333333-3333-4333-8333-333333333333")


def _org_row() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": ORG_ID,
        "name": "IdeaSense Lab",
        "slug": "ideasense-lab",
        "settings": {"locale": "en"},
        "created_at": now,
        "updated_at": now,
    }


class PlatformOrgsServiceTests(unittest.TestCase):
    def test_row_to_platform_org_payload_defaults_empty_values(self) -> None:
        payload = row_to_platform_org_payload({"id": ORG_ID})

        self.assertEqual(payload["id"], ORG_ID)
        self.assertEqual(payload["name"], "")
        self.assertEqual(payload["slug"], "")
        self.assertEqual(payload["settings"], {})

    def test_build_platform_org_filters_includes_trimmed_search(self) -> None:
        where_clause, params = build_platform_org_filters(
            limit=20,
            offset=5,
            q=" Lab ",
        )

        self.assertIn("deleted_at IS NULL", where_clause)
        self.assertIn("name ILIKE :search", where_clause)
        self.assertEqual(params["limit"], 20)
        self.assertEqual(params["offset"], 5)
        self.assertEqual(params["search"], "%Lab%")

    def test_fetch_platform_orgs_payload_returns_list_metadata(self) -> None:
        session = _Session([[{"total": 1}], [_org_row()]])

        payload = _run(
            fetch_platform_orgs_payload(
                session,
                limit=20,
                offset=0,
                q="Lab",
            )
        )

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["limit"], 20)
        self.assertEqual(payload["orgs"][0]["slug"], "ideasense-lab")
        self.assertEqual(session.params[0]["search"], "%Lab%")
        self.assertEqual(session.params[1]["search"], "%Lab%")

    def test_update_platform_org_rejects_empty_name(self) -> None:
        session = _Session([])

        with self.assertRaises(PlatformOrgValidationError) as exc:
            _run(
                update_platform_org_payload(
                    session,
                    org_id=ORG_ID,
                    name="  ",
                    settings=None,
                )
            )

        self.assertEqual(exc.exception.detail, "Organization name is required")
        self.assertEqual(session.params, [])

    def test_update_platform_org_rejects_non_object_settings(self) -> None:
        session = _Session([])

        with self.assertRaises(PlatformOrgValidationError) as exc:
            _run(
                update_platform_org_payload(
                    session,
                    org_id=ORG_ID,
                    name=None,
                    settings="bad",  # type: ignore[arg-type]
                )
            )

        self.assertEqual(exc.exception.detail, "settings must be an object")
        self.assertEqual(session.params, [])

    def test_update_platform_org_raises_not_found(self) -> None:
        session = _Session([[]])

        with self.assertRaises(PlatformOrgNotFoundError) as exc:
            _run(
                update_platform_org_payload(
                    session,
                    org_id=ORG_ID,
                    name="IdeaSense Lab",
                    settings={"locale": "en"},
                )
            )

        self.assertEqual(exc.exception.detail, "Organization not found")
        self.assertEqual(session.params[0]["org_id"], str(ORG_ID))

    def test_update_platform_org_returns_payload(self) -> None:
        session = _Session([[_org_row()]])

        payload = _run(
            update_platform_org_payload(
                session,
                org_id=ORG_ID,
                name=" IdeaSense Lab ",
                settings={"locale": "en"},
            )
        )

        self.assertEqual(payload["name"], "IdeaSense Lab")
        self.assertEqual(payload["settings"], {"locale": "en"})
        self.assertEqual(
            session.params[0],
            {
                "org_id": str(ORG_ID),
                "name": "IdeaSense Lab",
                "settings": {"locale": "en"},
            },
        )


def _run(awaitable):
    return asyncio.run(awaitable)


class _Session:
    def __init__(self, results: list[list[dict]]) -> None:
        self.results = list(results)
        self.params: list[dict] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.params.append(params or {})
        rows = self.results.pop(0) if self.results else []
        return _Result(rows)


class _Result:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def mappings(self) -> "_Result":
        return self

    def all(self) -> list[dict]:
        return self.rows

    def first(self) -> dict | None:
        return self.rows[0] if self.rows else None


if __name__ == "__main__":
    unittest.main()
