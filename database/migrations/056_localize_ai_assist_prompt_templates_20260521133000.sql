-- 056) Ensure AI-assist drafts honor the requested output language.
--
-- Older active DB prompt templates forced AI-assist drafts to English, which
-- overrode file prompts in hybrid prompt mode. Only patch those legacy rows.

SELECT set_config('app.actor_type', 'system', false);

UPDATE prompt_templates
SET content = $$You draft a possible answer the user can edit. Use only the provided context and follow the prompt's required structure.

Write every visible word in {{output_language}}. If {{output_language}} is Simplified Chinese, translate all headings, labels, examples, and helper phrases into Simplified Chinese; do not leave labels such as "Actor", "Context", "Trigger", or "Consequence" in English. If key details are missing, use short placeholders in the same language, or mark an assumption with "(Assumption)" in English and "(假设)" in Simplified Chinese.

Keep it concise and concrete (1-3 short paragraphs or short bullets if the prompt uses bullets). Avoid boilerplate phrasing. Do not invent facts. Do not mention schema paths or internal IDs. Return only the answer text.$$,
    updated_at = now()
WHERE template_key = 'chat.ai_assist_system'
  AND deleted_at IS NULL
  AND content ILIKE '%Write in English only%';

UPDATE prompt_templates
SET content = $$Output language: {{output_language}}.
Prompt: {{prompt}}
Validation rule: {{validation_rule}}
Instruction: {{instruction}}

{{context_block}}{{sentence_hint}}
If the prompt, validation rule, or instruction are written in a different language from the output language, preserve the meaning and structure but translate the draft into the requested output language. All headings and labels must also use the requested output language.

Return only the draft answer text.$$,
    updated_at = now()
WHERE template_key = 'chat.ai_assist_user'
  AND deleted_at IS NULL
  AND content ILIKE '%Language: {{language_hint}}%';
