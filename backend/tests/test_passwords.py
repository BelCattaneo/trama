from trama.passwords import hash_password, verify_password


def test_hash_has_bcrypt_prefix():
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$2b$12$")


def test_round_trip():
    plaintext = "correct horse battery staple"
    assert verify_password(plaintext, hash_password(plaintext)) is True


def test_wrong_password_fails():
    hashed = hash_password("right")
    assert verify_password("wrong", hashed) is False


def test_verify_is_idempotent():
    hashed = hash_password("repeat me")
    assert verify_password("repeat me", hashed) is True
    assert verify_password("repeat me", hashed) is True


def test_empty_string_round_trip():
    hashed = hash_password("")
    assert verify_password("", hashed) is True
    assert verify_password("not empty", hashed) is False


def test_same_password_yields_different_hashes():
    a = hash_password("salt me")
    b = hash_password("salt me")
    assert a != b
    assert verify_password("salt me", a) is True
    assert verify_password("salt me", b) is True
