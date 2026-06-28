import os
import unittest

from app.core.email_sender import (
    log_email_diagnostics,
    send_password_reset_email,
    send_verification_email,
)


class EmailSenderLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original = {
            key: os.environ.get(key)
            for key in (
                "APP_ENV",
                "EMAIL_FROM",
                "EMAIL_LOG_TOKEN_LINKS",
                "EMAIL_REPLY_TO",
                "EMAIL_VERIFY_BASE_URL",
                "RESEND_API_KEY",
            )
        }
        os.environ["APP_ENV"] = "development"
        os.environ["EMAIL_VERIFY_BASE_URL"] = "http://localhost:3000"
        os.environ.pop("RESEND_API_KEY", None)
        os.environ.pop("EMAIL_LOG_TOKEN_LINKS", None)

    def tearDown(self) -> None:
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_verification_email_does_not_log_token_link_by_default(self) -> None:
        with self.assertLogs("app.core.email_sender", level="INFO") as logs:
            send_verification_email(
                to_email="founder@example.com",
                token="verify-secret-token",
            )

        rendered_logs = "\n".join(logs.output)
        self.assertNotIn("verify-secret-token", rendered_logs)
        self.assertNotIn("verify-email?token=", rendered_logs)
        self.assertNotIn("verify-email#token=", rendered_logs)
        self.assertNotIn("founder@example.com", rendered_logs)

    def test_password_reset_email_logs_token_link_when_explicitly_allowed(
        self,
    ) -> None:
        os.environ["EMAIL_LOG_TOKEN_LINKS"] = "1"

        with self.assertLogs("app.core.email_sender", level="INFO") as logs:
            send_password_reset_email(
                to_email="founder@example.com",
                token="reset-secret-token",
            )

        rendered_logs = "\n".join(logs.output)
        self.assertIn("reset-secret-token", rendered_logs)
        self.assertIn("reset-password#token=", rendered_logs)

    def test_token_link_logging_flag_is_ignored_in_production(self) -> None:
        from app.core import email_sender

        os.environ["APP_ENV"] = "production"
        os.environ["EMAIL_LOG_TOKEN_LINKS"] = "1"
        os.environ["RESEND_API_KEY"] = "test-resend-key"
        os.environ["EMAIL_FROM"] = "IdeaSense AI <no-reply@example.com>"

        original_resend = email_sender.resend

        class FakeEmails:
            @staticmethod
            def send(payload):
                raise RuntimeError("simulated-send-failure")

        class FakeResend:
            api_key = None
            Emails = FakeEmails

        with self.assertLogs("app.core.email_sender", level="ERROR") as logs:
            try:
                email_sender.resend = FakeResend
                with self.assertRaises(RuntimeError):
                    send_verification_email(
                        to_email="founder@example.com",
                        token="verify-secret-token",
                    )
            finally:
                email_sender.resend = original_resend

        rendered_logs = "\n".join(logs.output)
        self.assertNotIn("verify-secret-token", rendered_logs)
        self.assertNotIn("verify-email?token=", rendered_logs)
        self.assertNotIn("verify-email#token=", rendered_logs)

    def test_reply_to_is_included_when_configured(self) -> None:
        from app.core import email_sender

        os.environ["RESEND_API_KEY"] = "test-resend-key"
        os.environ["EMAIL_FROM"] = "IdeaSense AI <no-reply@mg.ideasenseai.com>"
        os.environ["EMAIL_REPLY_TO"] = "ideasenseai@gmail.com"
        sent_payloads = []
        original_resend = email_sender.resend

        class FakeEmails:
            @staticmethod
            def send(payload):
                sent_payloads.append(payload)
                return {"id": "email_test"}

        class FakeResend:
            api_key = None
            Emails = FakeEmails

        try:
            email_sender.resend = FakeResend
            send_verification_email(
                to_email="founder@example.com",
                token="verify-secret-token",
            )
        finally:
            email_sender.resend = original_resend

        self.assertEqual(sent_payloads[0]["reply_to"], "ideasenseai@gmail.com")

    def test_email_diagnostics_do_not_log_secret_or_addresses(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["RESEND_API_KEY"] = "re_test_secret_123456789"
        os.environ["EMAIL_FROM"] = "IdeaSense AI <no-reply@example.com>"
        os.environ["EMAIL_REPLY_TO"] = "reply@example.com"
        os.environ["EMAIL_VERIFY_BASE_URL"] = "https://app.example.com"

        with self.assertLogs("uvicorn.error", level="WARNING") as logs:
            log_email_diagnostics()

        rendered_logs = "\n".join(logs.output)
        self.assertIn("RESEND_API_KEY_CONFIGURED=True", rendered_logs)
        self.assertIn("EMAIL_FROM_CONFIGURED=True", rendered_logs)
        self.assertNotIn("re_test_secret", rendered_logs)
        self.assertNotIn("no-reply@example.com", rendered_logs)
        self.assertNotIn("reply@example.com", rendered_logs)
        self.assertNotIn("https://app.example.com", rendered_logs)
