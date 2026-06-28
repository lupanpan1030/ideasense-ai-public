# Security Policy

IdeaSense AI handles account, organization, project, assessment, report, and
admin data. Treat security and privacy issues as high priority.

## Reporting

Do not disclose suspected vulnerabilities in public issues, public discussions,
screenshots, or exported public repositories.

For the private repository, report issues through the private maintainer channel
with:

- A short description of the issue.
- Affected route, feature, or file path.
- Steps to reproduce.
- Expected impact.
- Any safe logs or screenshots with secrets removed.

## Sensitive Data

Never commit or expose:

- Provider API keys.
- Database URLs.
- JWT or session secrets.
- Captcha or email provider secrets.
- Real user, project, report, or dogfooding evidence.
- Production smoke artifacts with private data.

Public-safe exports must follow
`docs/adr/0001-public-private-content-boundary.md`.

## Verification Expectations

Security-sensitive changes should include targeted tests or a documented manual
check. Auth, permissions, admin, report access, invite, email, password reset,
and public-export changes require explicit verification notes.
