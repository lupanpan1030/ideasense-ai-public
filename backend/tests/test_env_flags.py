import os
import unittest

from app.core.env import admin_api_enabled, sample_public_enabled


class SamplePublicEnabledTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original = {
            key: os.environ.get(key)
            for key in (
                "ADMIN_API_ENABLED",
                "ADMIN_ENABLED",
                "APP_ENV",
                "SAMPLE_PUBLIC_ENABLED",
            )
        }

    def tearDown(self) -> None:
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_defaults_to_disabled_in_production(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ.pop("SAMPLE_PUBLIC_ENABLED", None)
        self.assertFalse(sample_public_enabled())

    def test_defaults_to_enabled_outside_production(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ.pop("SAMPLE_PUBLIC_ENABLED", None)
        self.assertTrue(sample_public_enabled())

    def test_explicit_enable_overrides_production_default(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["SAMPLE_PUBLIC_ENABLED"] = "1"
        self.assertTrue(sample_public_enabled())

    def test_explicit_disable_overrides_non_production_default(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["SAMPLE_PUBLIC_ENABLED"] = "0"
        self.assertFalse(sample_public_enabled())

    def test_admin_api_defaults_to_disabled_in_production(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ.pop("ADMIN_API_ENABLED", None)
        os.environ.pop("ADMIN_ENABLED", None)
        self.assertFalse(admin_api_enabled())

    def test_admin_api_requires_truthy_enable_in_production(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ADMIN_API_ENABLED"] = "1"
        self.assertTrue(admin_api_enabled())

    def test_admin_api_defaults_to_enabled_outside_production(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ.pop("ADMIN_API_ENABLED", None)
        os.environ.pop("ADMIN_ENABLED", None)
        self.assertTrue(admin_api_enabled())

    def test_admin_api_disable_overrides_non_production_default(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["ADMIN_API_ENABLED"] = "0"
        self.assertFalse(admin_api_enabled())


if __name__ == "__main__":
    unittest.main()
