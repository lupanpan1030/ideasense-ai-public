import json
import unittest
from unittest.mock import patch

from app.core.llm_parse_utils import (
    LLM_JSON_FALLBACK_LOG_CODE,
    parse_json_object,
)


class LlmParseUtilsTests(unittest.TestCase):
    def test_parse_json_object_accepts_clean_json(self) -> None:
        self.assertEqual(parse_json_object('{"status": "ok"}'), {"status": "ok"})

    def test_parse_json_object_recovers_prose_wrapped_json_with_warning(self) -> None:
        with self.assertLogs("app.core.llm_parse_utils", level="WARNING") as logs:
            parsed = parse_json_object('Here is the result: {"status": "ok"} Thanks.')

        self.assertEqual(parsed, {"status": "ok"})
        self.assertTrue(
            any(LLM_JSON_FALLBACK_LOG_CODE in message for message in logs.output)
        )

    def test_parse_json_object_accepts_code_fence_without_fallback(self) -> None:
        content = """```json
{"status": "ok"}
```"""
        with patch("app.core.llm_parse_utils.logger.warning") as warning:
            parsed = parse_json_object(content)

        self.assertEqual(parsed, {"status": "ok"})
        warning.assert_not_called()

    def test_parse_json_object_rejects_truncated_json(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            parse_json_object('{"status": "ok"')

    def test_parse_json_object_rejects_multiple_objects(self) -> None:
        with self.assertRaisesRegex(ValueError, "multiple or malformed JSON objects"):
            parse_json_object('{"status": "ok"} {"status": "duplicate"}')

    def test_parse_json_object_rejects_truncated_second_object(self) -> None:
        with self.assertRaisesRegex(ValueError, "multiple or malformed JSON objects"):
            parse_json_object('{"status": "ok"} {"status":')


if __name__ == "__main__":
    unittest.main()
