# SKURGE — THE BUSINESS OS (Web build)

This build preserves the original Python/Kivy project and adds a Flask browser interface using its existing SQLite schema and services.

## Run locally (Windows PowerShell)
1. Install Python 3.12+.
2. In this folder run `py -m venv .venv`, then `.\.venv\Scripts\Activate.ps1`.
3. Run `pip install -r requirements.txt`.
4. Set a local secret: `$env:SKURGE_SECRET_KEY = (py -c "import secrets; print(secrets.token_hex(32))")`.
5. Run `py web_app.py` and open `http://127.0.0.1:5000`.

## Main implemented browser flows
- Animated SKURGE splash → product welcome/explanation → login or registration.
- Business profile creation and editing.
- Dashboard powered by existing finance and employee services.
- Finance ledger: record income/expenses by category/date; totals use integer cents.
- Employees: add records, view status counts, update active/on-leave/inactive status, generate one-time referral codes that expire in seven days, and join using a code at registration.
- Settings: browser-persisted dark/light theme toggle and business switching where available.
- All original navigation sections remain accessible. Sections whose backend/services were not implemented in the original phases are explicitly presented as workspaces, not falsely represented as finished integrations.

## Important boundaries
CIPC, SARS, banks, PayShap, real payroll transfers, password reset and MFA are not connected by this project. Referral codes add a user as an employee member; the code is single-use and expires after seven days. The original Kivy source files and phase scripts are retained in this archive.
