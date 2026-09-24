import asyncio
from uuid import uuid4

import pytest


pytest.importorskip("aiosqlite")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from scripts.seed import main as seed_database  # noqa: E402


def test_catalog_recommendation_assistant_and_admin_flow():
    asyncio.run(seed_database())

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "usuario@teste.com", "password": "Teste123@"},
        )
        assert login.status_code == 200

        catalog = client.get("/api/v1/contents")
        assert catalog.status_code == 200
        assert catalog.json()["total"] >= 10

        preferences = client.put(
            "/api/v1/preferences",
            json={
                "preferred_domains": ["filme", "livro"],
                "preferred_categories": ["Ficção científica"],
            },
        )
        assert preferences.status_code == 200

        recommendations = client.get("/api/v1/recommendations")
        assert recommendations.status_code == 200
        assert recommendations.json()["items"]

        music_preferences = client.put(
            "/api/v1/preferences",
            json={"preferred_domains": ["musica"], "preferred_categories": []},
        )
        assert music_preferences.status_code == 200
        music_recommendations = client.get("/api/v1/recommendations")
        assert music_recommendations.status_code == 200
        assert music_recommendations.json()["items"][0]["content"]["domain"] == "musica"

        profile = client.patch(
            "/api/v1/auth/me",
            json={"name": "Usuário com Avatar", "avatar": "raposa"},
        )
        assert profile.status_code == 200
        assert profile.json()["avatar"] == "raposa"

        assistant = client.post(
            "/api/v1/assistant/chat",
            json={"message": "Quero uma indicação de ficção científica"},
        )
        assert assistant.status_code == 200
        assert assistant.json()["answer"]

        follow_up = client.post(
            "/api/v1/assistant/chat",
            json={"message": "Agora quero algo parecido, mas mais leve"},
        )
        assert follow_up.status_code == 200
        chat_history = client.get("/api/v1/assistant/history")
        assert chat_history.status_code == 200
        assert len(chat_history.json()) >= 4

        client.post("/api/v1/auth/logout")
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@recomenda.com", "password": "Admin123@"},
        )
        assert admin_login.status_code == 200

        statistics = client.get("/api/v1/admin/statistics")
        assert statistics.status_code == 200
        assert statistics.json()["contents"] >= 10

        suffix = uuid4().hex[:8]
        domain = client.post(
            "/api/v1/admin/domains",
            json={
                "code": f"podcast_{suffix}",
                "name": "Podcasts de teste",
                "description": "Domínio criado pelo teste automatizado.",
                "is_active": True,
            },
        )
        assert domain.status_code == 201
        domain_id = domain.json()["id"]
        domain_code = domain.json()["code"]

        content = client.post(
            "/api/v1/contents",
            json={
                "title": "Conteúdo administrativo de teste",
                "description": "Conteúdo criado para verificar o CRUD completo.",
                "domain": domain_code,
                "category": "Teste",
                "source_name": "pytest",
                "external_id": f"content-{suffix}",
                "metadata": {},
                "is_published": True,
            },
        )
        assert content.status_code == 201
        content_id = content.json()["id"]

        updated = client.patch(
            f"/api/v1/contents/{content_id}",
            json={"title": "Conteúdo administrativo atualizado"},
        )
        assert updated.status_code == 200
        assert updated.json()["title"].endswith("atualizado")

        assert client.delete(f"/api/v1/contents/{content_id}").status_code == 204
        assert client.delete(f"/api/v1/admin/domains/{domain_id}").status_code == 204
