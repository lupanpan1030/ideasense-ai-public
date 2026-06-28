from typing import Any


def is_verifiable_question_instance(status: Any, final_answer_text: Any) -> bool:
    if not isinstance(status, str) or status.strip().lower() != "answered":
        return False
    if not isinstance(final_answer_text, str):
        return False
    return bool(final_answer_text.strip())
