# AGIseed

![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml/badge.svg)

AGIseed: Evolutionary neural topologies dashboard and Academy.

Quick start (local):

- Start services with Docker Compose:

```bash
docker compose up -d
```

- Run E2E tests (Playwright) locally:

```bash
# from repository root
make e2e
```

Or on Windows (PowerShell):

```powershell
.\scripts\run_e2e.ps1
```

Notes:
- Replace `<OWNER>/<REPO>` in the badge URL with your GitHub repository owner and name to enable the CI badge.
- CI will build backend and frontend, run tests, bring up containers and execute Playwright E2E tests.
