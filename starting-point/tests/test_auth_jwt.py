from starting_point.auth.jwt import create_token, decode_token


def test_create_and_decode():
    token = create_token(user_id="u1")
    payload = decode_token(token)
    assert payload["sub"] == "u1"
    assert "exp" in payload


def test_decode_invalid_returns_none():
    result = decode_token("invalid.token.here")
    assert result is None
