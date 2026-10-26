"""
business_service.py

Business profile operations, now backed by persistent SQLite storage
(via BusinessRepository) instead of an in-memory dict.

Public API is intentionally unchanged from the Phase 8 in-memory
version (create_business, update_business, get_business_for_user)
so existing callers (BusinessSetupScreen, app.py) did not need to
change their call sites — only their imports, and only because
Business/registration-status constants moved to business_repository.

New in Phase 9: get_businesses_for_user (list, supports multiple
businesses per owner) and active-business selection, backed by the
session_state table.

Phase 11: creating a business now also grants its creator the
'owner' role in business_memberships — the real permission-bearing
record PermissionService checks. This is the ONLY place a membership
row is currently created; see permission_service.py's docstring for
what that means and does not yet mean.
"""

from services.business_repository import (
    Business,
    BusinessRepository,
    DRAFT,
    REGISTRATION_IN_PROGRESS,
    REGISTERED_DECLARED,
    VERIFIED,
    REGISTRATION_STATUSES,
    REGISTRATION_STATUS_CHOICES,
)
from services.database import get_connection
from services.permission_service import PermissionService


class BusinessService:
    """Business profile operations. Delegates all storage to BusinessRepository."""

    _repository = None

    @classmethod
    def _repo(cls) -> BusinessRepository:
        if cls._repository is None:
            cls._repository = BusinessRepository(get_connection())
        return cls._repository

    @classmethod
    def configure_repository(cls, repository: BusinessRepository) -> None:
        """Used by tests to inject a repository backed by a temporary database."""
        cls._repository = repository

    @classmethod
    def create_business(cls, owner_user_id: str, **fields) -> Business:
        if not fields.get("name", "").strip():
            raise ValueError("Business name is required.")
        business = cls._repo().create(owner_user_id=owner_user_id, **fields)
        PermissionService.grant_owner(business_id=business.id, user_id=owner_user_id)
        return business

    @classmethod
    def update_business(cls, business_id: str, **fields) -> Business:
        updated = cls._repo().update(business_id, **fields)
        if updated is None:
            raise ValueError("No business found with that ID.")
        return updated

    @classmethod
    def get_business_for_user(cls, owner_user_id: str):
        """Returns the user's ACTIVE business, or their most recently
        updated one if no active selection has been made yet."""
        businesses = cls._repo().get_by_owner(owner_user_id)
        if not businesses:
            return None

        active_id = cls._repo().get_active_business_id(owner_user_id)
        if active_id:
            for business in businesses:
                if business.id == active_id:
                    return business
        return businesses[0]  # Most recently updated, per get_by_owner's ORDER BY.

    @classmethod
    def get_businesses_for_user(cls, owner_user_id: str):
        """Returns ALL businesses owned by this user (supports multiple businesses)."""
        return cls._repo().get_by_owner(owner_user_id)

    @classmethod
    def set_active_business(cls, owner_user_id: str, business_id: str) -> Business:
        business = cls._repo().get_by_id(business_id)
        if business is None or business.owner_user_id != owner_user_id:
            raise ValueError("That business does not belong to this user.")
        cls._repo().set_active_business_id(owner_user_id, business_id)
        return business
