Version: v5.3.7
Date: 2026-01-07
Status: Approved for Implementation (Stage 1)
Scope: Stage 1/2/3 master specs + data contracts (DVF).
Source of truth: docs/spec/MASTER_SPEC.md in the private repository; public-safe
exports use docs/spec/PUBLIC_SPEC.md as the available summary.
Principle 1: Any new/renamed field must land in the private Master Spec first;
otherwise it is a bug. Public-safe summaries should be mirrored into PUBLIC_SPEC
when the public contract description changes.
Principle 2: Backward-incompatible schema changes require a new version and explicit migration notes.
Principle 3: Default mode is No Search; any external-data usage must be explicitly flagged per spec.
Principle 4: Null-Safe Logic is mandatory; null inputs must not crash and must not coerce to 0.
Principle 5: Unknown is a valid user input; routing must degrade gracefully (minimal-friction).
