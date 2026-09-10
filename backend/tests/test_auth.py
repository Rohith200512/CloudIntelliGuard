"""Tests for authentication API endpoints."""
import pytest


@pytest.mark.asyncio
async def test_login_success(client, seeded_db):
    from app.core.config import settings
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == settings.admin_username


@pytest.mark.asyncio
async def test_login_wrong_password(client, seeded_db):
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody", "password": "pass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_without_token(client):
    resp = await client.get("/api/v1/datasets")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_token(client, auth_headers):
    resp = await client.get("/api/v1/datasets", headers=auth_headers)
    assert resp.status_code == 200
