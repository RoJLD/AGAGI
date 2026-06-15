.PHONY: e2e hooks

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
