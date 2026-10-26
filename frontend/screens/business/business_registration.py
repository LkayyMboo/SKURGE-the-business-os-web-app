"""
business_registration.py

Business setup screen — collects the new business's basic profile
right after sign-up/sign-in. Pure data entry: NO CIPC/SARS
verification happens here.

Phase 9: registration status is now one of the explicit backend
status codes (business_repository.DRAFT / REGISTRATION_IN_PROGRESS /
REGISTERED_DECLARED) rather than a free-text string the UI invented.
REGISTERED_DECLARED is explicitly labeled "as declared by you" —
SKURGE has not verified this with CIPC. VERIFIED is never offered
here; nothing in this app can set it yet.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget

from components.base.background_mixin import BackgroundColorMixin
from components.buttons.buttons import PrimaryButton
from components.inputs.inputs import TextInputField
from services.business_repository import REGISTRATION_STATUS_CHOICES
from services.business_service import BusinessService
from styles.theme import Theme

# label (shown to user) -> status code (stored in the database)
_STATUS_LABEL_TO_CODE = {label: code for code, label in REGISTRATION_STATUS_CHOICES.items()}
_STATUS_LABELS = list(_STATUS_LABEL_TO_CODE.keys())

BUSINESS_TYPE_OPTIONS = ["Sole Proprietor", "Partnership", "Pty Ltd", "Co-operative", "Other"]
INDUSTRY_OPTIONS = ["Retail", "Services", "Food & Beverage", "Manufacturing", "Technology", "Agriculture", "Other"]
PROVINCE_OPTIONS = [
    "Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo",
    "Mpumalanga", "Northern Cape", "North West", "Western Cape",
]
TAX_STATUS_OPTIONS = ["Not registered", "Registered", "Not sure"]


def _labeled_spinner(label_text: str, options: list, default_text: str):
    """A label + Spinner pair, styled to match the rest of the inputs."""
    column = BoxLayout(
        orientation="vertical", size_hint=(1, None), height=62, spacing=Theme.dimensions.SPACE_XS
    )
    label = Label(
        text=label_text, color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.LABEL,
        size_hint=(1, None), height=18, halign="left", valign="middle",
    )
    label.bind(size=lambda *_: setattr(label, "text_size", label.size))
    spinner = Spinner(
        text=default_text, values=options, size_hint=(1, None),
        height=Theme.dimensions.INPUT_HEIGHT,
        background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
    )
    column.add_widget(label)
    column.add_widget(spinner)
    return column, spinner


class BusinessSetupScreen(BackgroundColorMixin, Screen):
    """Collects the new business's profile. Calls on_complete(business) when done."""

    def __init__(self, on_complete=None, **kwargs):
        super().__init__(**kwargs)
        self._on_complete = on_complete
        self._current_user = None
        self.set_background_color(Theme.colors.BACKGROUND)

        scroll = ScrollView(size_hint=(1, 1))

        outer = BoxLayout(orientation="vertical", size_hint=(1, None))
        outer.bind(minimum_height=outer.setter("height"))

        form = BoxLayout(
            orientation="vertical", size_hint=(None, None), width=480,
            spacing=Theme.dimensions.FIELD_SPACING, padding=(0, Theme.dimensions.SPACE_LG),
            pos_hint={"center_x": 0.5},
        )
        form.bind(minimum_height=form.setter("height"))

        title_label = Label(
            text="Tell us about your business", color=Theme.colors.TEXT_PRIMARY, bold=True,
            font_size=Theme.typography.TITLE, size_hint=(1, None), height=36,
        )
        subtitle_label = Label(
            text="This sets up your business profile. You can update it later in Business Settings.",
            color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY,
            size_hint=(1, None), height=40,
        )
        subtitle_label.bind(size=lambda *_: setattr(subtitle_label, "text_size", subtitle_label.size))
        title_spacer = Widget(size_hint=(1, None), height=Theme.dimensions.SECTION_SPACING)

        self.name_field = TextInputField(label="Business name *", placeholder="e.g. Khumalo Retail Pty Ltd")

        status_row, self.registration_status_spinner = _labeled_spinner(
            "Registration status *", _STATUS_LABELS, _STATUS_LABELS[0]
        )
        self.cipc_field = TextInputField(
            label="CIPC registration number (optional)",
            placeholder="Leave blank if not yet registered",
        )

        type_row, self.business_type_spinner = _labeled_spinner(
            "Business type *", BUSINESS_TYPE_OPTIONS, "Select business type"
        )
        industry_row, self.industry_spinner = _labeled_spinner(
            "Industry *", INDUSTRY_OPTIONS, "Select industry"
        )
        province_row, self.province_spinner = _labeled_spinner(
            "Province *", PROVINCE_OPTIONS, "Select province"
        )

        self.city_field = TextInputField(label="City / Town", placeholder="e.g. Mahikeng")
        self.primary_contact_field = TextInputField(
            label="Primary contact person", placeholder="e.g. Thandiwe Khumalo"
        )
        self.phone_field = TextInputField(label="Business phone", placeholder="e.g. 071 234 5678")
        self.contact_email_field = TextInputField(label="Business email", placeholder="e.g. info@business.co.za")

        tax_row, self.tax_status_spinner = _labeled_spinner(
            "Tax registration status (optional)", TAX_STATUS_OPTIONS, TAX_STATUS_OPTIONS[0]
        )

        self._error_label = Label(
            text="", color=Theme.colors.DANGER, font_size=Theme.typography.CAPTION,
            size_hint=(1, None), height=20,
        )

        continue_button = PrimaryButton(text="Continue to Dashboard")
        continue_button.width = 480
        continue_button.bind(on_release=lambda *_: self._attempt_submit())

        required_note = Label(
            text="* Required field", color=Theme.colors.TEXT_SECONDARY,
            font_size=Theme.typography.CAPTION, size_hint=(1, None), height=18,
        )

        for widget in [
            title_label, subtitle_label, title_spacer,
            self.name_field, status_row, self.cipc_field,
            type_row, industry_row, province_row, self.city_field,
            self.primary_contact_field, self.phone_field, self.contact_email_field,
            tax_row, required_note, self._error_label, continue_button,
        ]:
            form.add_widget(widget)

        outer.add_widget(form)
        scroll.add_widget(outer)
        self.add_widget(scroll)

    def set_current_user(self, user) -> None:
        """Called by app.py right before this screen is shown."""
        self._current_user = user
        if user and not self.contact_email_field.text:
            self.contact_email_field.text = user.email

    def _attempt_submit(self) -> None:
        self._error_label.text = ""

        name = self.name_field.text.strip()
        business_type = self.business_type_spinner.text
        industry = self.industry_spinner.text
        province = self.province_spinner.text
        phone = self.phone_field.text.strip()
        contact_email = self.contact_email_field.text.strip()

        if not name:
            self._error_label.text = "Business name is required."
            return
        if business_type == "Select business type":
            self._error_label.text = "Please select a business type."
            return
        if industry == "Select industry":
            self._error_label.text = "Please select an industry."
            return
        if province == "Select province":
            self._error_label.text = "Please select a province."
            return
        if not phone and not contact_email:
            self._error_label.text = "Please provide a business phone number or email."
            return
        if not self._current_user:
            self._error_label.text = "You must be signed in to continue."
            return

        registration_status_code = _STATUS_LABEL_TO_CODE[self.registration_status_spinner.text]

        try:
            business = BusinessService.create_business(
                owner_user_id=self._current_user.id,
                name=name,
                registration_status=registration_status_code,
                cipc_number=self.cipc_field.text.strip(),
                business_type=business_type,
                industry=industry,
                province=province,
                city=self.city_field.text.strip(),
                primary_contact_name=self.primary_contact_field.text.strip(),
                phone=phone,
                email=contact_email,
                tax_status=self.tax_status_spinner.text,
            )
        except ValueError as error:
            self._error_label.text = str(error)
            return

        if self._on_complete:
            self._on_complete(business)
