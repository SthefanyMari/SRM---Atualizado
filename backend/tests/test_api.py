import pytest


pytest.importorskip("aiosqlite")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_health_register_login_and_preferences():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["database"] == "connected"

        register = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Teste Automatizado",
                "email": "teste.automatizado@example.com",
                "password": "Teste123@",
            },
        )
        assert register.status_code in {201, 409}

        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "teste.automatizado@example.com",
                "password": "Teste123@",
            },
        )
        assert login.status_code == 200
        assert login.json()["user"]["email"] == "teste.automatizado@example.com"

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200

        preferences = client.put(
            "/api/v1/preferences",
            json={
                "preferred_domains": ["filme", "curso"],
                "preferred_categories": ["Tecnologia"],
            },
        )
        assert preferences.status_code == 200
        assert preferences.json()["preferred_domains"] == ["filme", "curso"]
