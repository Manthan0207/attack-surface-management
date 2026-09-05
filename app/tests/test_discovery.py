def test_create_domain_runs_discovery_and_creates_assets(client, admin_headers):
    created = client.post(
        "/domains",
        headers=admin_headers,
        json={"domain": "discover.example.com"},
    )
    assert created.status_code == 201
    domain = created.json()
    domain_id = domain["id"]

    detail = client.get(f"/domains/{domain_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "COMPLETED"

    scans = client.get(f"/domains/{domain_id}/scans", headers=admin_headers)
    assert scans.status_code == 200
    scan_body = scans.json()
    assert scan_body["total"] == 1
    assert scan_body["items"][0]["status"] == "COMPLETED"

    assets = client.get("/assets", headers=admin_headers, params={"domain_id": domain_id})
    assert assets.status_code == 200
    asset_body = assets.json()
    assert asset_body["total"] == 4
    types = {item["type"] for item in asset_body["items"]}
    assert types == {"A", "AAAA", "NS", "MX"}


def test_manual_scan_accepted_when_idle(client, admin_headers):
    created = client.post(
        "/domains",
        headers=admin_headers,
        json={"domain": "rescan.example.com"},
    )
    domain_id = created.json()["id"]

    # First auto-scan already completed via sync_discovery fixture.
    response = client.post(f"/domains/{domain_id}/scan", headers=admin_headers)
    assert response.status_code == 202
    assert response.json()["status"] == "PENDING"

    scans = client.get(f"/domains/{domain_id}/scans", headers=admin_headers)
    assert scans.json()["total"] == 2


def test_manual_scan_conflict_when_active(client, admin_headers, db, monkeypatch):
    created = client.post(
        "/domains",
        headers=admin_headers,
        json={"domain": "conflict.example.com"},
    )
    domain_id = created.json()["id"]

    # Prevent the second enqueue from completing so a PENDING scan remains active.
    monkeypatch.setattr("app.services.scan.enqueue_scan", lambda _scan_id: None)

    first = client.post(f"/domains/{domain_id}/scan", headers=admin_headers)
    assert first.status_code == 202

    second = client.post(f"/domains/{domain_id}/scan", headers=admin_headers)
    assert second.status_code == 409
    assert "already running" in second.json()["detail"].lower()


def test_assets_filter_by_type(client, admin_headers):
    created = client.post(
        "/domains",
        headers=admin_headers,
        json={"domain": "filter.example.com"},
    )
    domain_id = created.json()["id"]

    response = client.get(
        "/assets",
        headers=admin_headers,
        params={"domain_id": domain_id, "type": "A"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["type"] == "A"
    assert body["items"][0]["value"] == "93.184.216.34"
