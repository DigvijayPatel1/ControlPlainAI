from app.core.security import generate_api_key, verify_api_key


def test_api_key_generation_and_verification():
    raw_key, hashed_key = generate_api_key("test_user")
    assert raw_key.startswith("cp_test_user_")
    assert hashed_key != raw_key
    assert verify_api_key(raw_key, hashed_key)


def test_wrong_api_key_fails():
    _raw_key, hashed_key = generate_api_key("test_user")
    assert not verify_api_key("cp_test_user_wrong", hashed_key)
