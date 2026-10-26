"""
permission_service.py

The permission matrix, and the one place protected operations check
"is this authenticated user actually allowed to do this on this
business?" — not just "is this business currently selected?".

Selecting a business (app_session.current_business) is never, by
itself, proof of authorization. A protected service method must be
given the ACTING user's ID and check it here.

CURRENT LIMITATION (stated plainly, not hidden): the only way a
MembershipRepository row is ever created today is automatically, as
'owner', when BusinessService.create_business() runs. There is no
"invite a teammate to this business" screen yet. So in practice,
every authorized action today resolves to the business owner — the
Admin/Manager/Employee rows of the matrix below are implemented and
tested, but cannot currently be exercised by a second real user
through the UI. That is future work, not something this phase
pretends to have finished.
"""

from services.database import get_connection
from services.membership_repository import ADMIN, EMPLOYEE, MANAGER, MembershipRepository, OWNER

# Permission matrix: which roles may perform which protected operations.
PERMISSIONS = {
    "manage_employees": {OWNER, ADMIN},
    "change_employment_status": {OWNER, ADMIN},
    "record_transactions": {OWNER, ADMIN, MANAGER},
    "view_finance": {OWNER, ADMIN, MANAGER},
}


class PermissionError(Exception):
    """Raised when an authenticated user lacks permission for an operation."""


class PermissionService:
    """Checks whether a user may perform a given operation on a business."""

    _repository = None

    @classmethod
    def _repo(cls) -> MembershipRepository:
        if cls._repository is None:
            cls._repository = MembershipRepository(get_connection())
        return cls._repository

    @classmethod
    def configure_repository(cls, repository: MembershipRepository) -> None:
        """Used by tests to inject a repository backed by a temporary database."""
        cls._repository = repository

    @classmethod
    def grant_owner(cls, business_id: str, user_id: str) -> None:
        """Called once, automatically, when a business is created."""
        cls._repo().create(business_id=business_id, user_id=user_id, role=OWNER)

    @classmethod
    def get_role(cls, business_id: str, user_id: str):
        return cls._repo().get_role(business_id, user_id)

    @classmethod
    def has_permission(cls, business_id: str, user_id: str, permission: str) -> bool:
        if permission not in PERMISSIONS:
            raise ValueError(f"Unknown permission: {permission!r}")
        role = cls.get_role(business_id, user_id)
        if role is None:
            return False
        return role in PERMISSIONS[permission]

    @classmethod
    def require_permission(cls, business_id: str, user_id: str, permission: str) -> None:
        """Raises PermissionError if the user lacks the given permission."""
        if not cls.has_permission(business_id, user_id, permission):
            raise PermissionError(
                f"You do not have permission to perform this action on this business."
            )
