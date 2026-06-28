from __future__ import annotations

from typing import Any

from app.services.localization import OutputLocale, output_language_label
from app.services.prompt_runtime import PromptContextBuilder, render_prompt_messages


PROMPT_CONTEXT_BUILDER = PromptContextBuilder()


async def build_report_prompt(
    session,
    report_input: dict[str, Any],
    *,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
) -> list[dict[str, str]]:
    context = PROMPT_CONTEXT_BUILDER.final_report(
        report_input,
        output_language=output_language_label(output_locale),
    )
    return await render_prompt_messages(
        session,
        context,
        project_settings=project_settings,
    )
