from services.business_repository import BusinessRepository, DRAFT, REGISTERED_DECLARED
from services.database import get_connection


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


def test_create_business_persists_fields(business_repo):
    business = business_repo.create(owner_user_id="user-1", **_sample_fields())
    assert business.id
    assert business.name == "Khumalo Retail"
    assert business.registration_status == DRAFT


def test_create_rejects_invalid_registration_status(business_repo):
    try:
        business_repo.create(owner_user_id="user-1", **_sample_fields(registration_status="bogus"))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_get_by_id_retrieves_created_business(business_repo):
    created = business_repo.create(owner_user_id="user-1", **_sample_fields())
    fetched = business_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == created.name


def test_get_by_id_returns_none_for_missing_business(business_repo):
    assert business_repo.get_by_id("does-not-exist") is None


def test_update_changes_fields_without_duplicating_row(business_repo):
    created = business_repo.create(owner_user_id="user-1", **_sample_fields())
    updated = business_repo.update(created.id, name="Khumalo Retail (Pty) Ltd", registration_status=REGISTERED_DECLARED)
    assert updated.name == "Khumalo Retail (Pty) Ltd"
    assert updated.registration_status == REGISTERED_DECLARED
    assert updated.id == created.id  # same row, not a new one

    all_for_owner = business_repo.get_by_owner("user-1")
    assert len(all_for_owner) == 1


def test_update_missing_business_returns_none(business_repo):
    assert business_repo.update("does-not-exist", name="X") is None


def test_update_rejects_invalid_registration_status(business_repo):
    created = business_repo.create(owner_user_id="user-1", **_sample_fields())
    try:
        business_repo.update(created.id, registration_status="bogus")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_get_by_owner_supports_multiple_businesses(business_repo):
    business_repo.create(owner_user_id="user-1", **_sample_fields(name="Business A"))
    business_repo.create(owner_user_id="user-1", **_sample_fields(name="Business B"))
    business_repo.create(owner_user_id="user-2", **_sample_fields(name="Someone Else's Business"))

    user_1_businesses = business_repo.get_by_owner("user-1")
    assert len(user_1_businesses) == 2
    names = {b.name for b in user_1_businesses}
    assert names == {"Business A", "Business B"}


def test_empty_database_returns_empty_list(business_repo):
    assert business_repo.get_by_owner("nobody") == []


def test_active_business_selection_persists(business_repo):
    business = business_repo.create(owner_user_id="user-1", **_sample_fields())
    assert business_repo.get_active_business_id("user-1") is None

    business_repo.set_active_business_id("user-1", business.id)
    assert business_repo.get_active_business_id("user-1") == business.id

    # Switching again updates rather than erroring/duplicating.
    business_2 = business_repo.create(owner_user_id="user-1", **_sample_fields(name="Second Business"))
    business_repo.set_active_business_id("user-1", business_2.id)
    assert business_repo.get_active_business_id("user-1") == business_2.id


def test_data_survives_closing_and_reopening_database(tmp_path):
    db_path = tmp_path / "persist_test.db"

    connection_1 = get_connection(db_path=db_path)
    repo_1 = BusinessRepository(connection_1)
    created = repo_1.create(owner_user_id="user-1", **_sample_fields())
    connection_1.close()

    connection_2 = get_connection(db_path=db_path)
    repo_2 = BusinessRepository(connection_2)
    fetched = repo_2.get_by_id(created.id)
    connection_2.close()

    assert fetched is not None
    assert fetched.name == created.name
    assert fetched.id == created.id
