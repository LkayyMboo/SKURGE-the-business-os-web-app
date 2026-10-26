from services.business_repository import DRAFT, REGISTERED_DECLARED


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


def test_create_business_valid(business_service):
    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    assert business.name == "Khumalo Retail"


def test_create_business_rejects_empty_name(business_service):
    try:
        business_service.create_business(owner_user_id="user-1", **_sample_fields(name="   "))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_update_business(business_service):
    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    updated = business_service.update_business(business.id, registration_status=REGISTERED_DECLARED)
    assert updated.registration_status == REGISTERED_DECLARED


def test_update_missing_business_raises(business_service):
    try:
        business_service.update_business("does-not-exist", name="X")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_get_business_for_user_returns_none_when_no_business(business_service):
    assert business_service.get_business_for_user("nobody") is None


def test_get_business_for_user_returns_active_business(business_service):
    b1 = business_service.create_business(owner_user_id="user-1", **_sample_fields(name="First"))
    b2 = business_service.create_business(owner_user_id="user-1", **_sample_fields(name="Second"))

    business_service.set_active_business("user-1", b1.id)
    assert business_service.get_business_for_user("user-1").id == b1.id

    business_service.set_active_business("user-1", b2.id)
    assert business_service.get_business_for_user("user-1").id == b2.id


def test_get_businesses_for_user_lists_all(business_service):
    business_service.create_business(owner_user_id="user-1", **_sample_fields(name="First"))
    business_service.create_business(owner_user_id="user-1", **_sample_fields(name="Second"))
    businesses = business_service.get_businesses_for_user("user-1")
    assert len(businesses) == 2


def test_set_active_business_rejects_other_users_business(business_service):
    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    try:
        business_service.set_active_business("user-2", business.id)
        assert False, "expected ValueError"
    except ValueError:
        pass
