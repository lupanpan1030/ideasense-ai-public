import os
import unittest

from app.services.org_invite_links import (
    InviteLinkConfigurationError,
    build_invite_link,
)


class OrgInviteLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original = {
            key: os.environ.get(key)
            for key in (
                "APP_BASE_URL",
                "APP_ENV",
                "FRONTEND_URL",
                "NEXT_PUBLIC_APP_URL",
            )
        }

    def tearDown(self) -> None:
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_non_production_defaults_to_localhost(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ.pop("APP_BASE_URL", None)
        os.environ.pop("FRONTEND_URL", None)
        os.environ.pop("NEXT_PUBLIC_APP_URL", None)

        self.assertEqual(
            build_invite_link("token-123"),
            "http://localhost:3000/join?token=token-123",
        )

    def test_production_requires_app_base_url(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ.pop("APP_BASE_URL", None)
        os.environ.pop("FRONTEND_URL", None)
        os.environ.pop("NEXT_PUBLIC_APP_URL", None)

        with self.assertRaises(InviteLinkConfigurationError) as raised:
            build_invite_link("token-123")

        self.assertIn("APP_BASE_URL is required", str(raised.exception))

    def test_production_rejects_localhost_app_base_url(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["APP_BASE_URL"] = "http://localhost:3000"

        with self.assertRaises(InviteLinkConfigurationError) as raised:
            build_invite_link("token-123")

        self.assertIn("public app URL", str(raised.exception))

    def test_production_uses_configured_public_app_base_url(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["APP_BASE_URL"] = "https://app.example.com/"

        self.assertEqual(
            build_invite_link("token-123"),
            "https://app.example.com/join?token=token-123",
        )


if __name__ == "__main__":
    unittest.main()
