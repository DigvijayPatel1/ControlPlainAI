"""
End-to-end backend verification.

Run this against a real, migrated Postgres + Redis (the same DATABASE_URL /
REDIS_URL your .env points at) to confirm the whole backend works *before*
touching the frontend. If this file passes, any bug you hit later is a
frontend integration issue, not a backend one.

    cd backend
    alembic upgrade head          # once, or after any new migration
    pytest tests/test_e2e_full_flow.py -v

Each test function is independent (uses its own randomly-generated email),
so you can re-run this file as many times as you want without resetting
the database.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _unique_email() -> str:
    return f"e2e-{uuid.uuid4().hex[:10]}@example.com"


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    r = await client.get("/health/database")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    r = await client.get("/health/redis")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_register_returns_token_user_and_api_key(client: AsyncClient):
    r = await client.post(
        "/auth/register",
        json={"email": _unique_email(), "full_name": "Ada Lovelace", "password": "password123"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["access_token"]
    assert body["user"]["role"] == "user"
    assert body["api_key"]["raw_key"].startswith("cp_")
    assert body["api_key"]["principal_id"] == body["user"]["default_principal_id"]


async def test_duplicate_email_is_rejected(client: AsyncClient):
    email = _unique_email()
    payload = {"email": email, "full_name": "Grace Hopper", "password": "password123"}
    r1 = await client.post("/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/auth/register", json=payload)
    assert r2.status_code == 409


async def test_login_with_wrong_password_is_rejected(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/auth/register", json={"email": email, "full_name": "Alan Turing", "password": "correct-password"}
    )
    r = await client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert r.status_code == 401


async def test_full_journey_jwt_and_api_key_share_one_principal(client: AsyncClient):
    """The dashboard (JWT) and the extension (API key) must see the same
    account, role, and budget — this is the piece that's easy to break."""
    register = await client.post(
        "/auth/register",
        json={"email": _unique_email(), "full_name": "Katherine Johnson", "password": "password123"},
    )
    assert register.status_code == 201
    body = register.json()
    jwt_headers = {"Authorization": f"Bearer {body['access_token']}"}
    api_key = body["api_key"]["raw_key"]

    me = await client.get("/auth/me", headers=jwt_headers)
    assert me.status_code == 200
    assert me.json()["email"] == body["user"]["email"]

    summary = await client.get("/v1/analytics/summary", headers=jwt_headers)
    assert summary.status_code == 200, summary.text

    budget = await client.get("/v1/budget", headers=jwt_headers)
    assert budget.status_code == 200, budget.text
    assert budget.json()["configured"] is True

    guarded = await client.post(
        "/guardrails/input",
        headers={"X-API-Key": api_key},
        json={"prompt": "What's a safe way to store user passwords?", "model": "gpt-4o-mini"},
    )
    assert guarded.status_code == 200, guarded.text
    assert guarded.json()["verdict"] in {"pass", "mask", "review", "block"}

    reviews_jwt = await client.get("/v1/admin/reviews", headers=jwt_headers)
    assert reviews_jwt.status_code == 403
    reviews_key = await client.get("/v1/admin/reviews", headers={"X-API-Key": api_key})
    assert reviews_key.status_code == 403


async def test_api_key_rotation_invalidates_the_old_key(client: AsyncClient):
    register = await client.post(
        "/auth/register",
        json={"email": _unique_email(), "full_name": "Radia Perlman", "password": "password123"},
    )
    body = register.json()
    jwt_headers = {"Authorization": f"Bearer {body['access_token']}"}
    old_key = body["api_key"]["raw_key"]

    rotate = await client.post("/auth/api-key/rotate", headers=jwt_headers)
    assert rotate.status_code == 200, rotate.text
    new_key = rotate.json()["api_key"]["raw_key"]
    assert new_key != old_key

    old_check = await client.get("/v1/budget", headers={"X-API-Key": old_key})
    assert old_check.status_code == 403

    new_check = await client.get("/v1/budget", headers={"X-API-Key": new_key})
    assert new_check.status_code == 200


async def test_requests_endpoint_is_scoped_to_the_caller(client: AsyncClient):
    """Regression test for the auth bug: /api/requests used to return
    everyone's history to anyone. Two different users must never see each
    other's requests."""
    alice = await client.post(
        "/auth/register", json={"email": _unique_email(), "full_name": "Alice", "password": "password123"}
    )
    bob = await client.post(
        "/auth/register", json={"email": _unique_email(), "full_name": "Bob", "password": "password123"}
    )
    alice_key = alice.json()["api_key"]["raw_key"]
    bob_key = bob.json()["api_key"]["raw_key"]

    await client.post(
        "/v1/chat/completions",
        headers={"X-API-Key": alice_key},
        json={
            "messages": [
                {"role": "user", "content": "Please charge my card 4111 1111 1111 1111 for the invoice."}
            ],
            "model": "auto",
        },
    )

    bob_requests = await client.get("/api/requests", headers={"X-API-Key": bob_key})
    assert bob_requests.status_code == 200
    assert all(item["principal_id"] != alice.json()["user"]["default_principal_id"] for item in bob_requests.json()["items"])

    alice_requests = await client.get("/api/requests", headers={"X-API-Key": alice_key})
    assert alice_requests.status_code == 200
    assert len(alice_requests.json()["items"]) >= 1


async def test_unauthenticated_requests_are_rejected(client: AsyncClient):
    """Regression test: these two endpoints used to have no auth at all."""
    r1 = await client.get("/api/requests")
    assert r1.status_code == 401
    r2 = await client.get("/api/reviews")
    assert r2.status_code == 401