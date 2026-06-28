# Question Bank Schema

Defines versioned question banks, valid stage/variant combinations, and
individual questions with capture metadata.

## Scope
- `question_bank_versions`
- `question_bank_stage_variants`
- `question_bank_questions`

## Conventions
- Global banks use `org_id = NULL`. `scope_org_id` normalizes scope with
  `COALESCE(org_id, ZERO_UUID)` for uniqueness constraints.
- `bank_key` is stored in lowercase and trimmed (enforced by CHECK).
- `bank_key` disallows whitespace; use lowercase slugs.
- `is_active` is enforced with a trigger that maintains `activated_at` and
  `deactivated_at` (only set on active -> inactive), plus CHECK constraints for
  consistency.

## Notes
- Stage/variant whitelist defaults to:
  - `problem/market/report`: `default`
  - `tech`: `default`, `router`, `pro`, `lite`
- `answer_examples` (`JSONB[]`) and `expected_patch_example` (`JSONB`) are
  reserved for extraction validation and regression checks.
