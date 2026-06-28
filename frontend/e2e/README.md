# Frontend E2E

Playwright tests live in this directory.

Run the stable browser smoke suite:

```bash
npm --prefix frontend run e2e
```

Install the Chromium browser binary if this machine has not run Playwright
before:

```bash
npm --prefix frontend run e2e:install
```

Run with a visible browser:

```bash
npm --prefix frontend run e2e:headed
```

By default Playwright uses `localhost:3002` and reuses an already running
Next.js dev server. If nothing is running there, it starts one.
To test an already running server, set:

```bash
PLAYWRIGHT_BASE_URL=http://localhost:3000 PLAYWRIGHT_SKIP_WEB_SERVER=1 npm --prefix frontend run e2e
```

The smoke tests intentionally avoid requiring a live backend. Add full-flow
tests separately when the backend, remote database, and test LLM provider are
available.
