"""
employees_screen.py

Employee management for the active business: summary counts, an
add-employee form, and a list of recorded employees with the ability
to change employment status.

Every mutating action (add, change status) passes
app_session.current_user.id as acting_user_id — EmployeeService
checks real permissions against business_memberships before doing
anything, it does not just trust that this screen is open.

IMPORTANT: changing an employee's "Role" dropdown here is an HR
label only. It does NOT grant that person any system permission —
see services/employee_repository.py's docstring. This screen does
not pretend otherwise; there is no "make this an admin login" control
here, because no such feature exists yet.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from app.session import app_session
from components.buttons.buttons import PrimaryButton, SecondaryButton
from components.cards.card import Card, StatCard
from components.inputs.inputs import TextInputField
from components.tables.table import DataTable
from screens.base_screen import BaseScreen
from services.employee_repository import ACTIVE, EMPLOYEE_ROLES, EMPLOYMENT_STATUSES, INACTIVE, ON_LEAVE
from services.employee_service import EmployeeService
from services.permission_service import PermissionError
from styles.theme import Theme
from utils.validators import validate_iso_date

ROLE_LABELS = {"owner": "Owner", "admin": "Admin", "manager": "Manager", "employee": "Employee"}
ROLE_BY_LABEL = {label: code for code, label in ROLE_LABELS.items()}

STATUS_LABELS = {ACTIVE: "Active", INACTIVE: "Inactive", ON_LEAVE: "On Leave"}
STATUS_BY_LABEL = {label: code for code, label in STATUS_LABELS.items()}


class EmployeesScreen(BaseScreen):
    """Employee management for the active business."""

    def __init__(self, **kwargs):
        super().__init__(
            title="Employees", subtitle="Manage who works at your business", **kwargs
        )
        self._render()

    def _render(self) -> None:
        """(Re)builds this screen's entire content from current data."""
        self.content.clear_widgets()
        business = app_session.current_business

        if business is None:
            self.content.add_widget(
                Label(
                    text="No active business. Complete business setup first.",
                    color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY,
                )
            )
            return

        scroll = ScrollView(size_hint=(1, 1))
        body = BoxLayout(
            orientation="vertical", spacing=Theme.dimensions.SECTION_SPACING, size_hint=(1, None)
        )
        body.bind(minimum_height=body.setter("height"))

        body.add_widget(self._build_summary_row(business.id))
        body.add_widget(self._build_add_form(business.id))
        body.add_widget(self._build_employee_list(business.id))

        scroll.add_widget(body)
        self.content.add_widget(scroll)

    def _build_summary_row(self, business_id: str):
        counts = EmployeeService.get_counts(business_id)
        row = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=100,
            spacing=Theme.dimensions.SPACE_MD,
        )
        row.add_widget(StatCard(
            label="Active", value=str(counts["active"]),
            accent_color=Theme.colors.SAGE, size_hint=(1, 1),
        ))
        row.add_widget(StatCard(label="On Leave", value=str(counts["on_leave"]), size_hint=(1, 1)))
        row.add_widget(StatCard(label="Inactive", value=str(counts["inactive"]), size_hint=(1, 1)))
        return row

    def _build_add_form(self, business_id: str):
        card = Card(title="Add Employee", size_hint=(1, None), height=460)

        name_field = TextInputField(label="Full name", placeholder="e.g. Thandiwe Khumalo")
        email_field = TextInputField(label="Email (optional)", placeholder="e.g. thandiwe@example.com")
        phone_field = TextInputField(label="Phone (optional)", placeholder="e.g. 071 234 5678")
        job_title_field = TextInputField(label="Job title", placeholder="e.g. Sales Associate")

        role_spinner = Spinner(
            text=ROLE_LABELS["employee"], values=list(ROLE_LABELS.values()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        status_spinner = Spinner(
            text=STATUS_LABELS[ACTIVE], values=list(STATUS_LABELS.values()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        start_date_field = TextInputField(label="Start date (YYYY-MM-DD)", placeholder="e.g. 2026-10-11")

        error_label = Label(
            text="", color=Theme.colors.DANGER, font_size=Theme.typography.CAPTION,
            size_hint=(1, None), height=20,
        )

        def on_submit(*_args):
            error_label.text = ""
            user = app_session.current_user

            if user is None:
                error_label.text = "You must be signed in to add an employee."
                return
            if not name_field.text.strip():
                error_label.text = "Full name is required."
                return
            if not job_title_field.text.strip():
                error_label.text = "Job title is required."
                return
            try:
                start_date = validate_iso_date(start_date_field.text).isoformat()
            except ValueError as error:
                error_label.text = str(error)
                return

            try:
                EmployeeService.add_employee(
                    acting_user_id=user.id, business_id=business_id,
                    full_name=name_field.text.strip(), job_title=job_title_field.text.strip(),
                    role=ROLE_BY_LABEL[role_spinner.text],
                    employment_status=STATUS_BY_LABEL[status_spinner.text],
                    start_date=start_date, email=email_field.text.strip(), phone=phone_field.text.strip(),
                )
            except PermissionError as error:
                error_label.text = str(error)
                return
            except ValueError as error:
                error_label.text = f"Could not save: {error}"
                return

            self._render()  # Refresh in place — same pattern as FinanceScreen.

        submit_button = PrimaryButton(text="Add Employee")
        submit_button.width = 440
        submit_button.bind(on_release=on_submit)

        for widget in [
            name_field, email_field, phone_field, job_title_field,
            role_spinner, status_spinner, start_date_field, error_label, submit_button,
        ]:
            card.add_widget(widget)

        return card

    def _build_employee_list(self, business_id: str):
        employees = EmployeeService.list_employees(business_id)

        if not employees:
            card = Card(title="Employees", size_hint=(1, None), height=90)
            card.add_widget(
                Label(
                    text="No employees recorded yet.", color=Theme.colors.TEXT_SECONDARY,
                    font_size=Theme.typography.BODY,
                )
            )
            return card

        rows = [
            (e.full_name, e.job_title, ROLE_LABELS[e.role], STATUS_LABELS[e.employment_status], e.start_date)
            for e in employees
        ]
        card = Card(title="Employees", size_hint=(1, None), height=90 + min(len(rows), 10) * 40 + 70)
        card.add_widget(
            DataTable(
                columns=["Name", "Job Title", "Role", "Status", "Start Date"],
                rows=rows,
                size_hint=(1, None),
                height=40 + min(len(rows), 10) * 40,
            )
        )
        card.add_widget(self._build_status_change_row(business_id, employees))
        return card

    def _build_status_change_row(self, business_id: str, employees: list):
        """A simple control to change one employee's employment status
        without a separate detail screen — picks an employee by name,
        picks a new status, applies it."""
        row = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            spacing=Theme.dimensions.SPACE_SM,
        )
        names_to_ids = {e.full_name: e.id for e in employees}

        employee_spinner = Spinner(
            text=employees[0].full_name, values=list(names_to_ids.keys()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        new_status_spinner = Spinner(
            text=STATUS_LABELS[ACTIVE], values=list(STATUS_LABELS.values()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )

        def on_change_status(*_args):
            user = app_session.current_user
            if user is None:
                return
            employee_id = names_to_ids[employee_spinner.text]
            try:
                EmployeeService.set_employment_status(
                    acting_user_id=user.id, business_id=business_id,
                    employee_id=employee_id, employment_status=STATUS_BY_LABEL[new_status_spinner.text],
                )
            except (PermissionError, ValueError):
                pass  # Status-change row has no error label; a full detail screen is future work.
            self._render()

        change_button = SecondaryButton(text="Change Status")
        change_button.bind(on_release=on_change_status)

        row.add_widget(employee_spinner)
        row.add_widget(new_status_spinner)
        row.add_widget(change_button)
        return row
