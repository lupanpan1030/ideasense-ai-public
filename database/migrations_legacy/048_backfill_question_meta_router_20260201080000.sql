-- 048) backfill question_meta for router quick options (S3Q0)
UPDATE conversation_messages cm
SET meta = jsonb_set(
    COALESCE(cm.meta, '{}'::jsonb),
    '{question_meta}',
    jsonb_build_object(
        'question_id', q.question_id,
        'stage', q.stage,
        'variant', q.variant,
        'ui', q.prompt_meta->'ui'
    ),
    true
)
FROM projects p
JOIN question_bank_questions q
  ON q.bank_version_id = p.question_bank_version_id
 AND q.deleted_at IS NULL
WHERE cm.project_id = p.id
  AND cm.org_id = p.org_id
  AND cm.deleted_at IS NULL
  AND cm.role = 'assistant'
  AND (cm.meta->>'question_id') = 'S3Q0'
  AND q.question_id = (cm.meta->>'question_id')
  AND NOT (COALESCE(cm.meta, '{}'::jsonb) ? 'question_meta')
  AND (cm.meta IS NULL OR jsonb_typeof(cm.meta) = 'object')
  AND q.prompt_meta ? 'ui';
