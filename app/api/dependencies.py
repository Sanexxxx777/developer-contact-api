from ipaddress import ip_address, ip_network

from fastapi import Request

from app.services.contact_service import ContactService


def get_contact_service(request: Request) -> ContactService:
    return request.app.state.contact_service


def get_client_identity(request: Request) -> str:
    settings = request.app.state.settings
    peer = request.client.host if request.client else "unknown"
    if is_trusted_proxy(peer, settings.trusted_proxy_ips):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = forwarded.rsplit(",", 1)[-1].strip()
            try:
                return str(ip_address(candidate))
            except ValueError:
                pass
    return peer


def is_trusted_proxy(peer: str, trusted_entries: list[str]) -> bool:
    try:
        address = ip_address(peer)
        return any(address in ip_network(entry, strict=False) for entry in trusted_entries)
    except ValueError:
        return False
