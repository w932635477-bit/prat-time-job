from starting_point.auth.wechat import build_authorize_url, parse_callback_code


def test_build_authorize_url():
    url = build_authorize_url("http://localhost:8000/api/auth/wechat/callback")
    assert "open.weixin.qq.com" in url
    assert "snsapi_userinfo" in url
    assert "state=" in url


def test_parse_callback_code():
    code = parse_callback_code({"code": "abc123", "state": "xyz"})
    assert code == "abc123"


def test_parse_callback_code_missing():
    code = parse_callback_code({})
    assert code is None
