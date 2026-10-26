# SKURGE — THE BUSINESS OS

SKURGE currently has two entry points:

- **Android / desktop Kivy app:** `python frontend/main.py` (from the repository root; desktop Linux GUI requirements still apply).
- **Browser web adapter:** `python web_app.py` for local testing, or `gunicorn web_app:app` for deployment.

## Render deployment

1. Push this repository to GitHub, ensuring no local `venv/`, `.env`, or database file is committed.
2. In Render, create a Blueprint from the repository and use `render.yaml`, or create a Python web service manually.
3. Confirm `SKURGE_SECRET_KEY` is a unique generated secret, `SKURGE_DB_PATH=/var/data/skurge.db`, and a persistent disk is mounted at `/var/data`.
4. Deploy and check `/healthz`. Use the public HTTPS URL to test registration, login, business setup and dashboard.
5. Back up and migrate any local data separately if needed. The database included in older project archives may contain personal test records and must not be copied to a public repository.

## Important scope and security notes

The browser interface is an initial web adapter. It reuses the existing service layer for registration, login, business profile creation and dashboard summaries; it does **not** port every Kivy screen to the browser. Finance and employee data are displayed through the existing dashboard service. Other modules remain unimplemented in this web interface.

The existing authentication service documentation explicitly describes it as development-only. Before storing real company, financial, tax, or employee data, replace it with production-grade authentication (secure password verification, session expiry/revocation, password reset, stronger abuse controls and audit logging), review authorization end-to-end, add automated security tests, and plan a managed production database such as PostgreSQL. The included Render disk keeps SQLite data persistent for a single service instance, but SQLite on a disk is not a substitute for a multi-instance production database. CIPC, SARS, banking, payment and PayShap integrations are not connected by this deployment adapter.

## Android build

The existing Kivy app remains separate from the web adapter. Android builds should use Buildozer in Linux/WSL or a CI runner; a Render web service does not produce an APK. The GitHub Actions workflow checks the project structure only and is not yet an APK build pipeline.
