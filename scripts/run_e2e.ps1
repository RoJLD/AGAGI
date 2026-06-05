Param(
    [int]$WaitSeconds = 8
)

Write-Output "Starting services..."
docker compose up -d

Write-Output "Waiting for services to become ready ($WaitSeconds seconds)..."
Start-Sleep -Seconds $WaitSeconds

Push-Location ./frontend

Write-Output "Installing frontend dependencies..."
npm install

Write-Output "Installing Playwright browsers..."
npx playwright install --with-deps

Write-Output "Running Playwright E2E tests..."
npm run test:e2e

Pop-Location

Write-Output "Tearing down services..."
docker compose down
