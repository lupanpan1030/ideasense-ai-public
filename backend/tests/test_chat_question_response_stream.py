import unittest

from app.services.chat_stream.question_response import stream_question_response_events


class ChatQuestionResponseStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_question_response_events_streams_fallback_text(self) -> None:
        context = {
            "project_id": "project-1",
            "request_id": "request-1",
            "question_instance_id": "question-instance-1",
            "fallback_content": "What is the core customer pain?",
        }

        events = [
            event
            async for event in stream_question_response_events(
                context,
                actor_user_id="user-1",
            )
        ]

        joined = "".join(events)
        self.assertIn("event: assistant_first_token", joined)
        self.assertIn("event: token", joined)
        self.assertIn("What is the ", joined)
        self.assertIn("core customer ", joined)
        self.assertIn("pain?", joined)
        self.assertIn("event: assistant_done", joined)
        self.assertIn("request-1", joined)
        self.assertIn("project-1", joined)
