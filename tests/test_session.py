import pytest

from app.session import AppSession
from services.business_repository import DRAFT


def _sample_fields(**overrides):
    fields = dict(
        name="Khumalo Retail",
        business_type="Pty Ltd",
        industry="Retail",
        registration_status=DRAFT,
        province="Gauteng",
    )
    fields.update(overrides)
    return fields


@pytest.fixture
def session(business_service):
    s = AppSession()
    yield s
    s.clear()


def test_set_and_get_user(session):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    assert session.current_user.id == "user-1"


def test_require_business_raises_when_missing(session):
    with pytest.raises(ValueError):
        session.require_business()


def test_require_business_returns_active_business(session, business_service):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    session.set_business(business)
    assert session.require_business().id == business.id


def test_switch_business_updates_current_business(session, business_service):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    b1 = business_service.create_business(owner_user_id="user-1", **_sample_fields(name="First"))
    b2 = business_service.create_business(owner_user_id="user-1", **_sample_fields(name="Second"))

    session.set_business(b1)
    assert session.current_business.id == b1.id

    session.switch_business(b2.id)
    assert session.current_business.id == b2.id


def test_switch_business_without_user_raises(session):
    with pytest.raises(ValueError):
        session.switch_business("some-id")


def test_get_user_businesses_empty_without_user(session):
    assert session.get_user_businesses() == []


def test_get_user_businesses_lists_all(session, business_service):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    business_service.create_business(owner_user_id="user-1", **_sample_fields(name="First"))
    business_service.create_business(owner_user_id="user-1", **_sample_fields(name="Second"))
    assert len(session.get_user_businesses()) == 2


def test_clear_resets_user_and_business(session):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    session.clear()
    assert session.current_user is None
    assert session.current_business is None
