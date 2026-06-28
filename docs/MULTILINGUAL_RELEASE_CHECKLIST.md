# Multilingual Release Checklist

Use this checklist before calling the bilingual rollout complete on any environment.

## Goal

Verify that:

1. Locale is visible in the URL.
2. Locale persists across redirects and protected routes.
3. The rendered HTML matches the selected locale.
4. Public pages and login pages both behave correctly in `en` and `zh`.

## Automated Smoke Check

Run:

```bash
bash scripts/verify_multilingual_release.sh https://your-deployment.example.com
```

What it verifies:

1. `/` redirects to `/en`
2. `/projects` redirects to `/en/projects`
3. `/zh/projects` redirects to `/zh/login`
4. `/en/login` and `/zh/login` return `200`
5. `/en/methodology` and `/zh/methodology` return `200`
6. Rendered HTML includes matching `lang="..."` and `data-locale="..."`

## Manual QA

Check these in a browser:

1. Switch from `EN` to `中文` on marketing.
2. Confirm the URL changes and stays prefixed.
3. Switch from `EN` to `中文` in the workspace shell.
4. Switch from `EN` to `中文` in admin.
5. Open an existing project report generated in another language and confirm the mismatch notice appears.
6. Open stage summaries generated in another language and confirm the mismatch notice appears.
7. Refresh on a deep link such as `/zh/projects/<id>/report` and confirm locale stays correct.

## Notes

The current product rule is:

1. UI chrome follows the active locale.
2. Saved summaries and reports keep the locale used when they were generated.
3. Locale mismatch must be visible to the user rather than silently hidden.
