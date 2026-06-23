.PHONY: e2e hooks api-types edr-stubs

# Run E2E suite locally: starts docker compose, installs frontend deps, runs Playwright, tears down
e2e:
	@echo "Starting services..."
	docker compose up -d
	@echo "Waiting for services to become ready..."
	sleep 5
	@echo "Installing frontend dependencies..."
	npm --prefix frontend install
	@echo "Installing Playwright browsers..."
	npx playwright install --with-deps
	@echo "Running Playwright E2E tests..."
	npm --prefix frontend run test:e2e
	@echo "Tearing down..."
	docker compose down

# Active le hook git de parité (versionné dans hooks/). pre-commit -> parity_check (WARN, non bloquant).
hooks:
	git config core.hooksPath hooks
	@echo "Hooks actifs. pre-commit lance 'parity_check --staged --warn' (non bloquant ; --no-verify pour forcer)."

# Régénère les types TS depuis le schéma OpenAPI de FastAPI (dump -> openapi-typescript).
# La CI vérifie que le résultat est commité (git diff --exit-code) -> drift schéma↔types supprimé.
api-types:
	PYTHONPATH=. python tools/dump_openapi.py
	npm --prefix frontend run gen:api
	@echo "Types API régénérés : frontend/openapi.json + frontend/src/api/schema.ts"

# Scaffolde un stub de carte EDR pour chaque EDR documenté non curé (écrit edr_findings.json).
# Les stubs apparaissent en section « non curés » du frontend ; reste à curer les `series`.
edr-stubs:
	PYTHONPATH=. python tools/parity_check.py --fix
