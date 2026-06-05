.PHONY: e2e

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
