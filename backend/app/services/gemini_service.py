from __future__ import annotations

import asyncio
import json
import logging


from google import genai
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models import (
    Content,
    Interaction,
    RecommendationFeedback,
    UserPreference,
)

logger = logging.getLogger(__name__)


class GeminiRecommendation(BaseModel):
    content_id: int
    score: float = Field(ge=0, le=1)
    reason: str = Field(min_length=5, max_length=300)


class GeminiRecommendationList(BaseModel):
    recommendations: list[GeminiRecommendation]


_client = (
    genai.Client(api_key=settings.gemini_api_key)
    if settings.gemini_api_key
    else None
)


def gemini_is_enabled() -> bool:
    return _client is not None


def _content_to_dict(content: Content) -> dict:
    return {
        "id": content.id,
        "titulo": content.title,
        "descricao": content.description[:700],
        "dominio": content.domain,
        "categoria": content.category,
    }


async def rerank_recommendations(
    candidates: list[tuple[Content, float, str]],
    preference: UserPreference | None,
    interactions: list[Interaction],
    feedbacks: list[RecommendationFeedback],
    limit: int,
) -> list[tuple[Content, float, str]] | None:
    """
    Recebe candidatos produzidos pelo algoritmo local e pede ao Gemini
    para reorganizá-los de acordo com o perfil do usuário.

    Se o Gemini estiver indisponível, retorna None. Nesse caso, a rota
    continuará usando o algoritmo local.
    """

    if _client is None:
        return None

    profile = preference.profile if preference else {}

    ratings: dict[int, float] = {}
    recent_content_ids: list[int] = []
    recent_recommendation_ids: list[int] = []

    for interaction in interactions:
        interaction_type = str(interaction.interaction_type)

        if (
            interaction_type == "rating"
            and interaction.value is not None
            and interaction.content_id not in ratings
        ):
            ratings[interaction.content_id] = float(interaction.value)

        if interaction_type in {"view", "click"}:
            if interaction.content_id not in recent_content_ids:
                recent_content_ids.append(interaction.content_id)

        if interaction_type == "recommendation":
            if interaction.content_id not in recent_recommendation_ids:
                recent_recommendation_ids.append(interaction.content_id)

    feedback_by_content: dict[int, bool] = {}

    for feedback in feedbacks:
        feedback_by_content[feedback.content_id] = feedback.relevant

    catalog = [
        _content_to_dict(content)
        for content, _, _ in candidates
    ]

    context = {
        "preferencias": {
            "dominios": profile.get("preferred_domains", []),
            "categorias": profile.get("preferred_categories", []),
        },
        "avaliacoes": [
            {
                "content_id": content_id,
                "estrelas": rating,
            }
            for content_id, rating in ratings.items()
        ],
        "feedbacks": [
            {
                "content_id": content_id,
                "relevante": relevant,
            }
            for content_id, relevant in feedback_by_content.items()
        ],
        "conteudos_acessados_recentemente": recent_content_ids[:20],
        "recomendacoes_recentes": recent_recommendation_ids[:20],
        "quantidade_solicitada": limit,
        "catalogo_disponivel": catalog,
    }

    prompt = f"""
Você é o mecanismo inteligente de um sistema de recomendação multidomínio.

Os domínios disponíveis são:
- filmes;
- músicas;
- livros;
- cursos;
- produtos.

Sua tarefa é escolher e ordenar conteúdos que realmente combinem com
as preferências e o comportamento do usuário.

Regras obrigatórias:

1. Use somente IDs presentes em "catalogo_disponivel".
2. Nunca invente títulos ou IDs.
3. Respeite principalmente os domínios e categorias escolhidos.
4. Dê mais importância para avaliações altas e feedbacks relevantes.
5. Evite conteúdos marcados como não relevantes.
6. Evite repetir excessivamente recomendações recentes.
7. Produza uma justificativa curta, personalizada e em português.
8. Retorne no máximo {limit} recomendações.
9. O score deve ficar entre 0 e 1.

Dados para análise:

{json.dumps(context, ensure_ascii=False, indent=2)}
""".strip()

    try:
        interaction = await asyncio.wait_for(
            _client.aio.interactions.create(
                model=settings.gemini_model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": GeminiRecommendationList.model_json_schema(),
                },
            ),
            timeout=15,
        )

        if not interaction.output_text:
            return None

        parsed = GeminiRecommendationList.model_validate_json(
            interaction.output_text
        )

        content_by_id = {
            content.id: content
            for content, _, _ in candidates
        }

        selected: list[tuple[Content, float, str]] = []
        selected_ids: set[int] = set()

        for recommendation in parsed.recommendations:
            content = content_by_id.get(recommendation.content_id)

            if content is None:
                continue

            if content.id in selected_ids:
                continue

            selected.append(
                (
                    content,
                    recommendation.score,
                    recommendation.reason.strip(),
                )
            )
            selected_ids.add(content.id)

            if len(selected) >= limit:
                break

    
        for content, score, reason in candidates:
            if len(selected) >= limit:
                break

            if content.id in selected_ids:
                continue

            selected.append((content, score, reason))
            selected_ids.add(content.id)

        return selected if selected else None

    except Exception as exc:
        logger.warning(
            "Não foi possível gerar recomendações com o Gemini: %s",
            exc,
        )
        return None


async def generate_assistant_answer(prompt: str) -> str | None:
    """
    Envia uma pergunta ao Gemini.

    Retorna None quando a chave estiver ausente, a cota acabar
    ou acontecer algum erro. Assim o assistente local continua funcionando.
    """

    if _client is None:
        return None

    try:
        interaction = await asyncio.wait_for(
    _client.aio.interactions.create(
        model=settings.gemini_model,
        input=prompt,
    ),
    timeout=15,
)
        answer = interaction.output_text

        if not answer:
            return None

        return answer.strip()

    except Exception as exc:
        logger.warning(
            "Não foi possível consultar o assistente Gemini: %s",
            exc,
        )
        return None