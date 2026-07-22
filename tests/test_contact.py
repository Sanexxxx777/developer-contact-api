import json
from uuid import UUID


def test_contact_success_uses_ai_fallback_and_sends_two_emails(client, settings, valid_payload):
    response = client.post("/api/contact", json=valid_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "accepted"
    assert body["ai_fallback_used"] is True
    assert body["ai"]["category"] == "other"
    assert response.headers["x-request-id"]

    email_entry = json.loads(settings.email_log_path.read_text().strip())
    assert email_entry["contact_id"] == body["id"]
    assert len(email_entry["recipients"]) == 2


def test_contact_validation_returns_consistent_error(client, valid_payload):
    valid_payload["email"] = "not-an-email"
    valid_payload["comment"] = "short"

    response = client.post("/api/contact", json=valid_payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    fields = {error["field"] for error in response.json()["error"]["details"]}
    assert {"email", "comment"}.issubset(fields)


def test_rate_limit_returns_429_and_retry_after(client, settings, valid_payload):
    settings.rate_limit_requests = 1
    assert client.post("/api/contact", json=valid_payload).status_code == 201

    response = client.post("/api/contact", json=valid_payload)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"
    assert int(response.headers["retry-after"]) > 0


def test_email_failure_is_recorded_and_returns_503(client, monkeypatch, valid_payload):
    service = client.app.state.contact_service

    async def fail_delivery(*_args, **_kwargs):
        raise RuntimeError("smtp unavailable")

    monkeypatch.setattr(service.email, "send_contact_emails", fail_delivery)
    response = client.post("/api/contact", json=valid_payload)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "email_delivery_failed"
    metrics = client.get("/api/metrics").json()
    assert metrics["failed_contacts"] == 1


def test_request_log_does_not_contain_contact_pii(client, settings, valid_payload):
    client.post("/api/contact", json=valid_payload)
    log = settings.request_log_path.read_text()

    assert valid_payload["email"] not in log
    assert valid_payload["phone"] not in log
    assert '"path": "/api/contact"' in log


def test_unsafe_request_id_is_replaced(client):
    response = client.get("/api/health", headers={"X-Request-ID": "spaces are not allowed"})

    assert response.headers["x-request-id"] != "spaces are not allowed"
    UUID(response.headers["x-request-id"])
