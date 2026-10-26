def test_register_creates_user(auth_service):
    user = auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    assert user.full_name == "Jane Doe"
    assert user.email == "jane@business.co.za"


def test_register_rejects_duplicate_email(auth_service):
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    try:
        auth_service.register("Someone Else", "jane@business.co.za", "anotherpassword")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_login_succeeds_with_correct_password(auth_service):
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    user = auth_service.login("jane@business.co.za", "supersecret1")
    assert user.email == "jane@business.co.za"


def test_login_fails_with_wrong_password(auth_service):
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    try:
        auth_service.login("jane@business.co.za", "wrongpassword")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_login_fails_for_unknown_email(auth_service):
    try:
        auth_service.login("ghost@business.co.za", "whatever")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_password_is_never_stored_in_plaintext(user_repo, auth_service):
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    record = user_repo.get_by_email("jane@business.co.za")
    assert record is not None
    assert record.password_hash != b"supersecret1"
    assert b"supersecret1" not in record.password_hash


def test_user_survives_service_restart_simulation(user_repo, auth_service):
    """Simulates an app restart: register, then force the in-memory
    cache to reload from the (same) database, confirming login still
    works without re-registering."""
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")

    # Simulate restart: clear the in-memory cache but keep the same DB.
    auth_service._users_by_email_cache = {}
    auth_service._cache_loaded = False

    user = auth_service.login("jane@business.co.za", "supersecret1")
    assert user.email == "jane@business.co.za"
