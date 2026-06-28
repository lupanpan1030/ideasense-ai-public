# ADR 0001: Public / Private Content Boundary

## Status

Accepted

Public-safe ADR allowlist: yes

## Context

IdeaSense AI is currently developed in a private production/IP repository. The
repository contains both product code and proprietary assessment content used by
the live product flow:

`project -> staged interview -> context extraction -> stage gate confirmation -> DVF scoring -> report`

Some parts of the system are appropriate for a public engineering showcase or
public-safe repository. Other parts are product IP, production evidence, or
internal operating material and must not be exposed by changing the visibility
of this repository.

## Decision

The private repository remains the source of truth for production development
and may retain the complete product implementation, proprietary content, and
internal evidence.

A public repository, if created, must be exported as a public-safe copy with a
clean initial commit. It must not reuse this repository's Git history, because
private content may exist in historical commits even if it is removed from the
latest tree.

The public-safe repository may include:

- App shell and route structure.
- Backend and frontend architecture examples.
- API contract examples and generated public API documentation.
- Demo scaffolding that uses synthetic content only.
- Tests and documentation that do not reveal proprietary assessment content or
  production evidence.

The public-safe repository must exclude:

- Proprietary question banks under `resources/question_bank/*`.
- Production prompt files under `backend/app/prompts/*`.
- Detailed assessment scripts and private product contracts in
  `docs/spec/MASTER_SPEC.md`.
- Scoring rules, rubrics, and report-generation instructions that reveal the
  private assessment method.
- Real reports, user/project data, dogfooding evidence, and production smoke
  artifacts.
- Internal runbooks or evidence paths that expose private deployment,
  operations, or evaluation details.
- Real person identifiers, real emails, production credentials, provider keys,
  database URLs, or private screenshots.

## Consequences

- The current repository should not be made public directly.
- Public-safe export work must treat private content as excluded by default and
  opt in only synthetic examples.
- Public replacements should be created separately, for example
  `resources/question_bank.example.yaml`, public prompt-contract documentation,
  or `docs/spec/PUBLIC_SPEC.md`.
- Code refactors remain separate work and should not be bundled with public
  boundary cleanup.
- If a future change moves production content loading out of this repository,
  that change must preserve the product flow and update this ADR or add a new
  ADR.
