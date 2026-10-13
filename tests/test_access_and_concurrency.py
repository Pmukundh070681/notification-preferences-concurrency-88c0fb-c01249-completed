"""Integration tests (need the seeded Postgres from scripts/init.sql)."""
import threading

from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings
from app.main import app

ACME = "a1000000-0000-0000-0000-000000000001"
GLOBEX = "b2000000-0000-0000-0000-000000000002"
ALICE = "c3000000-0000-0000-0000-000000000001"
BOB = "c3000000-0000-0000-0000-000000000002"
CAROL = "c3000000-0000-0000-0000-000000000003"
DAVE = "d4000000-0000-0000-0000-000000000001"


def hdr(user, tenant, role="user"):
    tok = jwt.encode({"user_id": user, "tenant_id": tenant, "role": role},
                     settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {tok}"}


def url(u):
    return f"/api/v1/users/{u}/preferences"


def code(resp):
    return resp.json()["error"]["code"]


client = TestClient(app)


def test_no_token_is_401_with_code():
    r = client.get(url(ALICE))
    assert r.status_code == 401 and code(r) == "AUTHENTICATION_REQUIRED"


def test_user_forbidden_with_reason_for_other_user_read_and_write():
    r = client.get(url(BOB), headers=hdr(ALICE, ACME))
    assert r.status_code == 403 and code(r) == "SELF_ONLY"
    r = client.put(url(BOB), json={"sms_enabled": True}, headers={**hdr(ALICE, ACME), "If-Match": '"1"'})
    assert r.status_code == 403 and code(r) == "SELF_ONLY"


def test_admin_cross_tenant_read_and_write_refused_and_data_untouched():
    admin = hdr(CAROL, ACME, "admin")
    r = client.get(url(DAVE), headers=admin)
    assert r.status_code == 403 and code(r) == "CROSS_TENANT_ACCESS"
    r = client.put(url(DAVE), json={"email_enabled": False}, headers={**admin, "If-Match": '"1"'})
    assert r.status_code == 403 and code(r) == "CROSS_TENANT_ACCESS"
    assert client.get(url(DAVE), headers=hdr(DAVE, GLOBEX)).json()["email_enabled"] is True


def test_forged_tenant_in_token_cannot_reach_other_tenant_user():
    # token claims Globex tenant but user_id of an Acme user: scoped query finds nothing
    r = client.get(url(ALICE), headers=hdr(DAVE, GLOBEX, "admin"))
    assert r.status_code == 403 and code(r) == "CROSS_TENANT_ACCESS"


def test_body_cannot_set_tenant_or_version():
    r = client.put(url(ALICE), json={"tenant_id": GLOBEX, "sms_enabled": True},
                   headers={**hdr(ALICE, ACME), "If-Match": '"1"'})
    assert r.status_code == 422


def test_stale_put_gets_412_with_current_version_and_changes_nothing():
    h = hdr(BOB, ACME)
    etag = client.get(url(BOB), headers=h).headers["etag"]
    assert client.put(url(BOB), json={"frequency": "weekly"}, headers={**h, "If-Match": etag}).status_code == 200
    r = client.put(url(BOB), json={"frequency": "never"}, headers={**h, "If-Match": etag})
    assert r.status_code == 412 and code(r) == "VERSION_CONFLICT"
    assert r.json()["error"]["details"]["current_version"] == int(etag.strip('"')) + 1
    assert client.get(url(BOB), headers=h).json()["frequency"] == "weekly"


def test_simultaneous_edits_exactly_one_wins():
    h = hdr(ALICE, ACME)
    etag = client.get(url(ALICE), headers=h).headers["etag"]
    start_version = int(etag.strip('"'))
    n, results, barrier = 6, [], threading.Barrier(6)

    def worker(i):
        c = TestClient(app)
        barrier.wait()
        r = c.put(url(ALICE), json={"sms_enabled": bool(i % 2)}, headers={**h, "If-Match": etag})
        results.append(r.status_code)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == [200] + [412] * (n - 1)
    assert client.get(url(ALICE), headers=h).json()["version"] == start_version + 1
