def test_health_and_empty_metrics(client):
    health = client.get("/api/health")
    metrics = client.get("/api/metrics")

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "database": "ok",
    }
    assert metrics.status_code == 200
    assert metrics.json()["total_contacts"] == 0


def test_metrics_aggregate_contact_category(client, valid_payload):
    client.post("/api/contact", json=valid_payload)

    metrics = client.get("/api/metrics").json()

    assert metrics["total_contacts"] == 1
    assert metrics["delivered_contacts"] == 1
    assert metrics["ai_fallbacks"] == 1
    assert metrics["by_category"] == {"other": 1}


def test_docs_use_pinned_swagger_assets(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui-dist@5.32.11/swagger-ui-bundle.js" in response.text
    assert "swagger-ui-dist@5.32.11/swagger-ui.css" in response.text
