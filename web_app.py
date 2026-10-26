"""Browser entry point for SKURGE — THE BUSINESS OS.

This web interface reuses the project's existing service and SQLite layers.
It is an initial deployment adapter, not a claim that every Kivy screen has
been ported to the browser or that the current authentication service is
production-hardened.
"""
from __future__ import annotations

import os
import sys
from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
if str(FRONTEND) not in sys.path:
    sys.path.insert(0, str(FRONTEND))

from services.auth_service import AuthService  # noqa: E402
from services.business_service import BusinessService  # noqa: E402
from services.business_repository import (  # noqa: E402
    DRAFT, REGISTRATION_IN_PROGRESS, REGISTERED_DECLARED, REGISTRATION_STATUS_CHOICES,
)
from services.dashboard_service import DashboardService  # noqa: E402


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    production = os.getenv("RENDER", "").lower() == "true" or os.getenv("FLASK_ENV") == "production"
    secret = os.getenv("SKURGE_SECRET_KEY")
    if production and not secret:
        raise RuntimeError("Set SKURGE_SECRET_KEY in the Render environment before deploying.")
    app.config.update(
        SECRET_KEY=secret or "local-development-only-change-me",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=production,
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    CSRFProtect(app)
    Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "service": "skurge-web"}, 200

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user"):
                flash("Please sign in to continue.", "info")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    SECTIONS = [
        ("dashboard", "Dashboard", "◈"), ("business", "Business", "▦"),
        ("employees", "Employees", "♙"), ("payroll", "Payroll", "＄"),
        ("finance", "Finance", "↗"), ("payments", "Payments", "⇄"),
        ("orders", "Orders", "▤"), ("inventory", "Inventory", "▧"),
        ("suppliers", "Suppliers", "◇"), ("customers", "Customers", "♧"),
        ("tax", "Tax", "§"), ("documents", "Documents", "▱"),
        ("calendar", "Calendar", "▦"), ("network", "Business Network", "◎"),
        ("notifications", "Notifications", "♢"), ("settings", "Settings", "⚙"),
    ]
    SECTION_DESCRIPTIONS = {
        "dashboard": "Your business at a glance, using the existing SKURGE dashboard service.",
        "business": "Manage the business profile connected to your workspace.",
        "employees": "Team records and employee management.",
        "payroll": "Payroll workspace and employee compensation workflow.",
        "finance": "Financial records, expenses, income and cash movement.",
        "payments": "Payment workflows. External payment providers are not connected by default.",
        "orders": "Order management workspace.",
        "inventory": "Stock and inventory workspace.",
        "suppliers": "Supplier records and relationships.",
        "customers": "Customer records and relationships.",
        "tax": "Tax workspace. SARS integration is not connected by default.",
        "documents": "Business documents and required records.",
        "calendar": "Business calendar and scheduling.",
        "network": "Business-to-business network workspace.",
        "notifications": "Workspace notifications.",
        "settings": "Account and workspace preferences.",
    }

    @app.get("/")
    def index():
        if session.get("user"):
            return redirect(url_for("splash"))
        return redirect(url_for("login"))

    @app.get("/splash")
    def splash():
        next_url = url_for("module_page", section="dashboard") if session.get("user") else url_for("login")
        return render_template("splash.html", next_url=next_url)

    @app.get("/app/<section>")
    @login_required
    def module_page(section):
        valid = {item[0] for item in SECTIONS}
        if section not in valid:
            return redirect(url_for("module_page", section="dashboard"))
        user = session["user"]
        business = BusinessService.get_business_for_user(user["id"])
        dashboard_data = DashboardService.get_dashboard_data(business) if section == "dashboard" else None
        label = dict((key, name) for key, name, _ in SECTIONS)[section]
        symbol = dict((key, sym) for key, _, sym in SECTIONS)[section]
        descriptions = SECTION_DESCRIPTIONS
        # Describe existing source functionality honestly; do not imply placeholder screens are complete.
        module_detail = descriptions[section]
        module_status = "Service-backed" if section in {"dashboard", "business", "finance", "employees"} else "Port in progress"
        return render_template("module.html", user=user, business=business, dashboard_data=dashboard_data,
                               sections=SECTIONS, active=section, label=label, symbol=symbol,
                               description=descriptions[section], module_detail=module_detail,
                               module_status=module_status)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            if len(password) < 12:
                flash("Use a password with at least 12 characters.", "error")
                return render_template("auth.html", mode="register")
            try:
                user = AuthService.register(full_name, email, password)
                session.clear()
                session["user"] = {"id": user.id, "full_name": user.full_name, "email": user.email}
                flash("Account created. Welcome to SKURGE.", "success")
                return redirect(url_for("business_setup"))
            except ValueError as exc:
                flash(str(exc), "error")
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            try:
                user = AuthService.login(request.form.get("email", ""), request.form.get("password", ""))
                session.clear()
                session["user"] = {"id": user.id, "full_name": user.full_name, "email": user.email}
                return redirect(url_for("splash"))
            except ValueError as exc:
                flash(str(exc), "error")
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("login"))

    @app.get("/dashboard")
    @login_required
    def dashboard():
        return redirect(url_for("module_page", section="dashboard"))

    @app.route("/business/setup", methods=["GET", "POST"])
    @login_required
    def business_setup():
        user = session["user"]
        existing = BusinessService.get_business_for_user(user["id"])
        if request.method == "POST":
            if existing:
                flash("A business profile already exists. Editing is not available in this web adapter yet.", "info")
                return redirect(url_for("dashboard"))
            fields = {
                "name": request.form.get("name", "").strip(),
                "business_type": request.form.get("business_type", "").strip(),
                "industry": request.form.get("industry", "").strip(),
                "registration_status": request.form.get("registration_status", DRAFT),
                "province": request.form.get("province", "").strip(),
                "cipc_number": request.form.get("cipc_number", "").strip(),
                "city": request.form.get("city", "").strip(),
                "phone": request.form.get("phone", "").strip(),
                "email": request.form.get("business_email", "").strip(),
                "primary_contact_name": user["full_name"],
                "tax_status": "",
            }
            allowed = {DRAFT, REGISTRATION_IN_PROGRESS, REGISTERED_DECLARED}
            if fields["registration_status"] not in allowed:
                fields["registration_status"] = DRAFT
            if not all(fields[key] for key in ("name", "business_type", "industry", "province")):
                flash("Please complete the business name, type, industry and province.", "error")
            else:
                try:
                    BusinessService.create_business(owner_user_id=user["id"], **fields)
                    flash("Business profile created.", "success")
                    return redirect(url_for("dashboard"))
                except ValueError as exc:
                    flash(str(exc), "error")
        return render_template("business_setup.html", user=user, existing=existing,
                               statuses=REGISTRATION_STATUS_CHOICES)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
