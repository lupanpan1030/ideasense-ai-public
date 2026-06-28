# Public Prompt Contract Example

Production prompt templates live under `backend/app/prompts/` in the private
repository and are not public-safe content.

A public-safe export may include this directory to explain the prompt-loading
boundary without exposing production prompt text. If a runnable public demo is
needed, add synthetic templates here or in the exported repository that preserve
the same task names and input/output shape, but do not copy or paraphrase the
private prompts.

Public examples may document:

- Expected template file naming.
- Required input variables.
- Expected output format at a high level.
- Safety requirements such as not inventing missing facts.

Public examples must not include:

- Production assessment wording.
- Scoring instructions.
- Report-generation instructions.
- Hidden prompt routing strategy.
- Real user, project, report, or provider evidence.
