def test_rbac_matrix(client, auth_tokens):
    admin_hdr = {"Authorization": f"Bearer {auth_tokens['admin']}"}
    officer_hdr = {"Authorization": f"Bearer {auth_tokens['officer']}"}
    senior_hdr = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}
    auditor_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    # 1. /api/users (Administrator only)
    # Admin allowed
    res_admin = client.get("/api/users", headers=admin_hdr)
    assert res_admin.status_code == 200

    # Officer forbidden
    res_officer = client.get("/api/users", headers=officer_hdr)
    assert res_officer.status_code == 403

    # Senior Auditor forbidden
    res_senior = client.get("/api/users", headers=senior_hdr)
    assert res_senior.status_code == 403

    # Auditor forbidden
    res_auditor = client.get("/api/users", headers=auditor_hdr)
    assert res_auditor.status_code == 403

    # Unauthenticated rejected
    res_unauth = client.get("/api/users")
    assert res_unauth.status_code in (401, 403)

    # 2. /api/settings update (Administrator only)
    new_val = '{"state":"Karnataka","test":true}'
    res_adm_set = client.put("/api/settings/local_body_terms", json={"value_json": new_val}, headers=admin_hdr)
    assert res_adm_set.status_code == 200

    res_aud_set = client.put("/api/settings/local_body_terms", json={"value_json": new_val}, headers=auditor_hdr)
    assert res_aud_set.status_code == 403

    # 3. /api/audit-trail/verify (All authenticated roles allowed)
    assert client.get("/api/audit-trail/verify", headers=admin_hdr).status_code == 200
    assert client.get("/api/audit-trail/verify", headers=officer_hdr).status_code == 200
    assert client.get("/api/audit-trail/verify", headers=senior_hdr).status_code == 200
    assert client.get("/api/audit-trail/verify", headers=auditor_hdr).status_code == 200
