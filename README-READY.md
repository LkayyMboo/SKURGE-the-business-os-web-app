# SKURGE — THE BUSINESS OS (Ready Web Build)

This is a **new working copy** of the project. The original Phase 1–11 Kivy/frontend folders, services, screen folders, shell scripts, tests, and navigation structure are retained. The web interface is added alongside them; the original frontend is not replaced.

## Main change

Owner registration now collects the owner login and business profile in one form. When registration succeeds, SKURGE creates the account and business profile and opens `/app/dashboard` directly. There is no mandatory second business-setup step for new owners. Employees can still register with a referral code supplied by their employer.

## Run locally (Windows)

1. Install Python 3.11 or 3.12.
2. Open a terminal in this folder.
3. Create and activate a virtual environment:
   - PowerShell: `py -m venv .venv`
   - PowerShell: `\.venv\Scripts\Activate.ps1`
4. Install dependencies: `python -m pip install -r requirements.txt`
5. Create a long random secret and set it before running:
   - PowerShell: `$env:SKURGE_SECRET_KEY = 'replace-with-a-long-random-secret'`
6. Start the web app: `python web_app.py`
7. Open `http://127.0.0.1:5000`.

Do not use the example secret in a public deployment. The production app refuses to start if `SKURGE_SECRET_KEY` is missing.

## Render deployment

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn web_app:app`
- Set `SKURGE_SECRET_KEY` in Render's environment variables.
- If you have a mounted persistent disk, set `SKURGE_DATABASE_PATH` to a database file on that disk (for example `/var/data/skurge.db`). Without persistent storage, SQLite data on a typical ephemeral service filesystem can be lost when the service is replaced or redeployed.

## Features available in this build

- Account registration and sign-in with password hashing and Flask-signed sessions.
- One-step owner registration plus business profile creation.
- Employee invitation by one-time referral code, employee records/statuses and role checks.
- Dashboard, finance ledger and totals, business profile, and persisted records for the remaining workspace modules.
- Responsive styling, theme switch, CSRF protection, request limits, and health endpoint (`/healthz`).
- Original Phase 1–11 Kivy source and services retained under `frontend/`, plus the backend structure and phase scripts.

## Honest integration boundaries

This is not a claim that external services have been connected. Live CIPC registration, SARS submissions, bank transfers, PayShap execution, and real payroll disbursements require approved credentials and provider integrations; this build does not pretend to perform them. Payroll, payments, tax, orders, inventory, suppliers, customers, documents, calendar and network screens provide workspace record tracking, not external execution.

## Tests

Run the Python service tests with `pytest -q`, using a Python environment with the packages in `requirements.txt` and Kivy installed for the original desktop `AppSession` test. The new web-registration tests are in `tests/test_web_registration.py`. A deployment should also be smoke-tested against its configured database and secret before it is treated as production-ready.
