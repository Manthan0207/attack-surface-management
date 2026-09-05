def test_create_domain_normalizes_fqdn(client, admin_headers):
    response = client.post(
        "/domains",
        headers=admin_headers,
        json={"domain": "Example.COM"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "example.com"
    assert body["status"] in {"PENDING", "RUNNING", "COMPLETED"}


def test_create_domain_invalid_fqdn(client, admin_headers):
    response = client.post(
        "/domains",
        headers=admin_headers,
        json={"domain": "not a domain"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid FQDN"


def test_create_domain_duplicate(client, admin_headers):
    payload = {"domain": "dup-domain.example.com"}
    assert client.post("/domains", headers=admin_headers, json=payload).status_code == 201
    response = client.post("/domains", headers=admin_headers, json=payload)
    assert response.status_code == 409


def test_get_domain_not_found(client, admin_headers):
    response = client.get(
        "/domains/00000000-0000-0000-0000-000000000099",
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_list_domains_search_and_pagination(client, admin_headers):
    client.post("/domains", headers=admin_headers, json={"domain": "alpha.example.com"})
    client.post("/domains", headers=admin_headers, json={"domain": "beta.example.com"})

    response = client.get(
        "/domains",
        headers=admin_headers,
        params={"search": "alpha", "page": 1, "limit": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "alpha.example.com"


def test_delete_domain(client, admin_headers):
    created = client.post(
        "/domains",
        headers=admin_headers,
        json={"domain": "delete-me.example.com"},
    )
    domain_id = created.json()["id"]
    response = client.delete(f"/domains/{domain_id}", headers=admin_headers)
    assert response.status_code == 204
    assert client.get(f"/domains/{domain_id}", headers=admin_headers).status_code == 404
