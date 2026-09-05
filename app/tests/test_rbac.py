def test_viewer_cannot_create_domain(client, viewer_headers):
    response = client.post(
        "/domains",
        headers=viewer_headers,
        json={"domain": "example.com"},
    )
    assert response.status_code == 403


def test_viewer_cannot_trigger_scan(client, admin_headers, viewer_headers):
    created = client.post(
        "/domains",
        headers=admin_headers,
        json={"domain": "viewer-block.example.com"},
    )
    assert created.status_code == 201
    domain_id = created.json()["id"]

    response = client.post(f"/domains/{domain_id}/scan", headers=viewer_headers)
    assert response.status_code == 403


def test_analyst_cannot_delete_domain(client, admin_headers, analyst_headers):
    created = client.post(
        "/domains",
        headers=admin_headers,
        json={"domain": "analyst-delete.example.com"},
    )
    assert created.status_code == 201
    domain_id = created.json()["id"]

    response = client.delete(f"/domains/{domain_id}", headers=analyst_headers)
    assert response.status_code == 403


def test_analyst_can_create_domain(client, analyst_headers):
    response = client.post(
        "/domains",
        headers=analyst_headers,
        json={"domain": "analyst-ok.example.com"},
    )
    assert response.status_code == 201


def test_viewer_can_list_domains(client, admin_headers, viewer_headers):
    client.post("/domains", headers=admin_headers, json={"domain": "list-me.example.com"})
    response = client.get("/domains", headers=viewer_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1
