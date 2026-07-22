from types import SimpleNamespace

from app.api.dependencies import get_client_identity, is_trusted_proxy
from app.core.config import Settings


def test_comma_separated_security_lists_from_environment(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://portfolio.example,https://admin.example")
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1,10.0.0.1")

    settings = Settings(_env_file=None)

    assert settings.allowed_origins == ["https://portfolio.example", "https://admin.example"]
    assert settings.trusted_proxy_ips == ["127.0.0.1", "10.0.0.1"]


def test_trusted_proxy_accepts_cidr_but_rejects_outsiders():
    trusted = ["127.0.0.1", "172.16.0.0/12"]

    assert is_trusted_proxy("172.18.0.1", trusted) is True
    assert is_trusted_proxy("203.0.113.10", trusted) is False
    assert is_trusted_proxy("not-an-ip", trusted) is False


def test_client_identity_uses_nearest_forwarded_address_from_trusted_proxy():
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=SimpleNamespace(trusted_proxy_ips=["172.16.0.0/12"]))
        ),
        client=SimpleNamespace(host="172.18.0.1"),
        headers={"x-forwarded-for": "198.51.100.77, 203.0.113.9"},
    )

    assert get_client_identity(request) == "203.0.113.9"


def test_client_identity_ignores_forwarded_header_from_untrusted_peer():
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=SimpleNamespace(trusted_proxy_ips=["172.16.0.0/12"]))
        ),
        client=SimpleNamespace(host="203.0.113.10"),
        headers={"x-forwarded-for": "198.51.100.77"},
    )

    assert get_client_identity(request) == "203.0.113.10"
