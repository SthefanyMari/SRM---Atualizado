import re

import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import ChatMessage, Content, User, UserPreference
from app.schemas import (
    AssistantRequest,
    AssistantResponse,
    AssistantSource,
    ChatMessagePublic,
)


router = APIRouter(prefix="/assistant", tags=["Assistente IA"])

STOP_WORDS = {
    "uma", "para", "que", "com", "por", "dos", "das", "quero",
    "gostaria", "sobre", "mais",
}


def _tokens(text: str) -> set[str]:
    return {
        word for word in re.findall(r"[a-zá-ú0-9]+", text.lower())
        if len(word) > 2 and word not in STOP_WORDS
    }


def _score_contents(
    message: str,
    contents: list[Content],
    history: list[ChatMessage],
    preferred_domains: set[str],
) -> list[Content]:
    current_tokens = _tokens(message)
    context_tokens: set[str] = set()
    for item in history[-4:]:
        if item.role == "user":
            context_tokens.update(_tokens(item.content))

    aliases = {
        "filme": {"filme", "filmes", "cinema"},
        "musica": {"musica", "música", "musicas", "músicas", "canção", "som"},
        "livro": {"livro", "livros", "leitura", "romance"},
        "curso": {"curso", "cursos", "aprender", "estudar", "aula"},
        "produto": {"produto", "produtos", "comprar", "equipamento"},
    }

    matches: list[tuple[float, Content]] = []
    for content in contents:
        content_tokens = _tokens(
            f"{content.title} {content.description} {content.domain} {content.category}"
        )
        score = len(current_tokens.intersection(content_tokens)) * 3.0
        score += len(context_tokens.intersection(content_tokens)) * 0.35
        if current_tokens.intersection(aliases.get(content.domain, set())):
            score += 4.0
        if content.domain in preferred_domains:
            score += 0.8
        matches.append((score, content))

    matches.sort(key=lambda item: (-item[0], item[1].title.lower()))
    positive = [content for score, content in matches if score > 0]
    return (positive or [content for _, content in matches])[:4]


def _local_answer(message: str, selected: list[Content], history: list[ChatMessage]) -> str:
    if not selected:
        return "O catálogo ainda está vazio. Peça ao administrador para cadastrar conteúdos primeiro."

    lowered = message.lower()
    if "compar" in lowered and len(selected) >= 2:
        first, second = selected[:2]
        return (
            f"Comparando {first.title} e {second.title}: {first.title} é da categoria "
            f"{first.category.lower()} e {second.title} é da categoria {second.category.lower()}. "
            f"Pelo seu pedido, eu começaria por {first.title}. Depois, você pode abrir os dois "
            "no catálogo e marcar qual foi mais relevante."
        )

    primary = selected[0]
    alternatives = ", ".join(item.title for item in selected[1:3])
    follow_up = any(item.role == "user" for item in history)
    prefix = "Considerando também nossa conversa, " if follow_up else ""
    answer = (
        f"{prefix}minha principal indicação é {primary.title}. "
        f"É um conteúdo de {primary.category.lower()}: {primary.description}"
    )
    if alternatives:
        answer += f" Como alternativas, veja também {alternatives}."
    answer += " Se quiser, diga se prefere algo mais leve, mais avançado ou de outra categoria."
    return answer


async def _online_answer(
    message: str,
    contents: list[Content],
    history: list[ChatMessage],
) -> str | None:
    if not settings.openai_api_key:
        return None
    catalog = "\n".join(
        f"- {item.title} | {item.domain} | {item.category} | {item.description}"
        for item in contents[:20]
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Você é o assistente do Sistema de Recomendação Multidomínio. "
                "Responda em português claro e use prioritariamente o catálogo abaixo. "
                "Não invente itens como se estivessem cadastrados.\n\nCATÁLOGO:\n" + catalog
            ),
        },
        *[
            {"role": item.role, "content": item.content}
            for item in history[-8:]
            if item.role in {"user", "assistant"}
        ],
        {"role": "user", "content": message},
    ]
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": settings.openai_model, "messages": messages, "temperature": 0.6},
            )
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"]).strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return None


@router.get("/history", response_model=list[ChatMessagePublic])
async def chat_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(60)
    )
    return list(reversed(result.scalars().all()))


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await db.execute(delete(ChatMessage).where(ChatMessage.user_id == user.id))
    await db.commit()


@router.post("/chat", response_model=AssistantResponse)
async def chat(
    payload: AssistantRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssistantResponse:
    contents_result = await db.execute(
        select(Content).where(Content.is_published.is_(True)).order_by(Content.title)
    )
    contents = list(contents_result.scalars().all())
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(12)
    )
    history = list(reversed(history_result.scalars().all()))
    preference = await db.scalar(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    preferred_domains = set((preference.profile if preference else {}).get("preferred_domains", []))
    selected = _score_contents(payload.message, contents, history, preferred_domains)

    answer = await _online_answer(payload.message, contents, history)
    provider = "online" if answer else "local"
    if not answer:
        answer = _local_answer(payload.message, selected, history)

    sources = [
        AssistantSource(content_id=item.id, title=item.title, domain=item.domain)
        for item in selected[:3]
    ]
    db.add(ChatMessage(user_id=user.id, role="user", content=payload.message, sources=[]))
    db.add(
        ChatMessage(
            user_id=user.id,
            role="assistant",
            content=answer,
            sources=[source.model_dump(mode="json") for source in sources],
        )
    )
    await db.commit()
    return AssistantResponse(answer=answer, sources=sources, provider=provider)
