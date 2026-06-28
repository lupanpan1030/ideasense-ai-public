.PHONY: architecture-check backend-install backend-check frontend-install frontend-lint frontend-test frontend-build frontend-e2e-smoke dev-e2e dev-e2e-servers public-export-leak-self-test public-export-check local-clean locale-release-check check

architecture-check:
	python scripts/architecture_guard.py

backend-install:
	python -m pip install --upgrade pip
	python -m pip install -r backend/requirements.txt
	python -m pip install pytest

backend-check:
	python -m compileall backend/app
	python -m pytest -q backend/tests

frontend-install:
	npm --prefix frontend install

frontend-lint:
	npm --prefix frontend run lint

frontend-test:
	npm --prefix frontend run test

frontend-build:
	npm --prefix frontend run typecheck
	npm --prefix frontend run build

frontend-e2e-smoke:
	npm --prefix frontend run e2e -- e2e/smoke.spec.ts

dev-e2e-servers:
	bash scripts/dev-e2e.sh

dev-e2e: dev-e2e-servers

public-export-leak-self-test:
	tmpdir=$$(mktemp -d /tmp/ideasense-public-leak-test.XXXXXX); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	printf '%s_%s\n' ideasense master > "$$tmpdir/leak.txt"; \
	if $${PYTHON:-python3} scripts/scan-public-export-leaks.py "$$tmpdir" --rules scripts/public-export-denylist.txt >"$$tmpdir/out" 2>&1; then \
		cat "$$tmpdir/out"; \
		echo "Expected public export leak scan to fail on sentinel leak." >&2; \
		exit 1; \
	fi

public-export-check: public-export-leak-self-test
	set -e; \
	tmpdir=$$(mktemp -d /tmp/ideasense-public-export-parent.XXXXXX); \
	destination="$$tmpdir/export"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	scripts/create-public-export.sh "$$destination"; \
	test -f "$$destination/LICENSE"; \
	test ! -f "$$destination/docs/PROJECT-MAP.md"; \
	test ! -f "$$destination/docs/adr/0002-database-connection-role-model.md"; \
	test ! -f "$$destination/docs/public-export.md"; \
	test ! -f "$$destination/docs/public-export-allowlist-review.md"; \
	test ! -f "$$destination/docs/public-readme.md"; \
	test ! -f "$$destination/AGENTS.md"; \
	test ! -e "$$destination/.vscode/settings.json"; \
	test ! -e "$$destination/lib"; \
	test ! -d "$$destination/openspec"; \
	test ! -f "$$destination/backend/tests/test_database_script_guards.py"; \
	test ! -f "$$destination/frontend/tests/production-smoke-contracts.test.mjs"

local-clean:
	bash scripts/clean-local-artifacts.sh

locale-release-check:
	@test -n "$(BASE_URL)" || (echo "BASE_URL is required, e.g. make locale-release-check BASE_URL=https://ideasense.ai" && exit 1)
	bash scripts/verify_multilingual_release.sh "$(BASE_URL)"

check: architecture-check backend-check frontend-lint frontend-test frontend-build
