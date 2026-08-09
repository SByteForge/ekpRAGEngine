from app.tenancy.auth import generate_api_key, hash_api_key


def test_generated_key_has_expected_prefix():
    key = generate_api_key()
    assert key.startswith("ekp_")


def test_generated_keys_are_unique():
    keys = {generate_api_key() for _ in range(100)}
    assert len(keys) == 100


def test_hash_is_deterministic():
    key = "ekp_test_key_12345"
    assert hash_api_key(key) == hash_api_key(key)


def test_different_keys_hash_differently():
    assert hash_api_key("ekp_key_one") != hash_api_key("ekp_key_two")


def test_hash_never_equals_the_raw_key():
    key = "ekp_test_key_12345"
    assert hash_api_key(key) != key


def test_hash_output_is_fixed_length_hex():
    assert len(hash_api_key("any_key")) == 64
    assert all(c in "0123456789abcdef" for c in hash_api_key("any_key"))
