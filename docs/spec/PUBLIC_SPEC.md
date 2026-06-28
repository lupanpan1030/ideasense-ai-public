# IdeaSense AI Public Spec

## Purpose

This public-safe spec describes the application shape and integration contract
without exposing the proprietary assessment content used by the private
production repository.

IdeaSense AI helps early-stage software founders and student teams review a
project idea through a structured assessment flow:

`project -> staged interview -> context extraction -> stage gate confirmation -> DVF scoring -> report`

## Public Scope

A public-safe repository may describe and demonstrate:

- Project creation and staged workspace navigation.
- A structured interview shell.
- Context extraction and review-gate mechanics.
- Report rendering and export scaffolding.
- API boundary examples and synthetic demo data.
- Testing, CI, and development workflow.

## Private Scope

The following remain private production/IP content and are not part of the
public spec:

- Production question banks.
- Production prompt templates.
- Detailed interview scripts.
- Scoring rubrics and report-generation instructions.
- Master implementation spec details that reveal proprietary assessment logic.
- Real user, project, report, dogfooding, or production smoke evidence.

## Public Replacement Contracts

Public exports should use synthetic replacement material:

- `resources/question_bank.example.yaml` for question-bank shape only.
- `backend/app/prompts.example/` for prompt-loading boundary documentation.
- Public API docs or generated OpenAPI output with private examples removed.

Synthetic examples must be clearly labeled as non-production content. They
should preserve file/data shapes enough for maintainers to understand how the
application is wired, but they must not copy or paraphrase private assessment
content.

## Non-Goals

- This spec does not define the full product method.
- This spec does not replace `docs/spec/MASTER_SPEC.md` inside the private
  production repository.
- This spec does not authorize changing this repository to public visibility.
- This spec does not require code refactors.
