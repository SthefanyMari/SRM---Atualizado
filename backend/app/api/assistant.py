import re
import unicodedata
import json

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

from app.services.gemini_service import generate_assistant_answer


router = APIRouter(prefix="/assistant", tags=["Assistente IA"])

STOP_WORDS = {
    "uma", "para", "que", "com", "por", "dos", "das", "quero",
    "gostaria", "sobre", "mais", "voce", "você", "pode", "algum",
    "alguma", "meu", "minha", "seu", "sua",
}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(character for character in normalized if unicodedata.category(character) != "Mn")


def _tokens(text: str) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9]+", _normalize(text))
        if len(word) > 2 and word not in STOP_WORDS
    }


def _small_talk_answer(message: str, user_name: str) -> str | None:
    normalized = _normalize(message).strip()
    words = set(re.findall(r"[a-z0-9]+", normalized))
    first_name = user_name.split()[0] if user_name else ""

    if words and words.issubset({"oi", "ola", "hey", "opa", "bom", "dia", "boa", "tarde", "noite"}):
        greeting = f", {first_name}" if first_name else ""
        return (
            f"Olá{greeting}! Posso indicar e comparar filmes, músicas, livros, cursos e produtos. "
            "O que você está com vontade de descobrir hoje?"
        )
    if words.intersection({"obrigado", "obrigada", "valeu", "agradecido", "agradecida"}):
        return "Por nada! Se quiser, posso trazer outra opção ou comparar os conteúdos que apareceram."
    if "tudo bem" in normalized or "como voce esta" in normalized:
        return "Tudo certo por aqui e pronto para ajudar. Você quer uma indicação ou deseja comparar conteúdos?"
    if (
        "o que voce faz" in normalized
        or "como voce funciona" in normalized
        or words.intersection({"ajuda", "ajudar", "opcoes", "funcoes"})
    ):
        return (
            "Eu uso o catálogo, suas preferências e o contexto da conversa para indicar ou comparar conteúdos. "
            "Você pode pedir, por exemplo: “um filme de ficção científica”, “um curso para iniciantes” "
            "ou “outra opção parecida”."
        )
    return None


def _score_contents(
    message: str,
    contents: list[Content],
    history: list[ChatMessage],
    preferred_domains: set[str],
) -> tuple[list[Content], bool]:
    current_tokens = _tokens(message)
    context_tokens: set[str] = set()
    for item in history[-4:]:
        if item.role == "user":
            context_tokens.update(_tokens(item.content))

    aliases = {
        "filme": {"filme", "filmes", "cinema", "assistir"},
        "musica": {"musica", "musicas", "cancao", "som", "ouvir"},
        "livro": {"livro", "livros", "leitura", "romance", "ler"},
        "curso": {"curso", "cursos", "aprender", "estudar", "aula"},
        "produto": {"produto", "produtos", "comprar", "equipamento", "dispositivo"},
    }

    mood_aliases = {
        "leve": {"comedia", "animacao", "fabula", "bossa", "mpb", "iniciante", "otimista"},
        "calmo": {"calma", "tranquila", "classica", "bossa", "contemplacao"},
        "tranquilo": {"calma", "tranquila", "classica", "bossa", "contemplacao"},
        "tecnologia": {"tecnologia", "programacao", "dados", "informatica", "computacao"},
        "fantasia": {"fantasia", "aventura", "fabula"},
    }

    requested_domains = {
        domain for domain, words in aliases.items() if current_tokens.intersection(words)
    }
    requested_moods = {
        mood for mood in mood_aliases if mood in current_tokens
    }
    recently_suggested: set[int] = set()
    for item in history[-6:]:
        if item.role == "assistant":
            recently_suggested.update(
                int(source["content_id"])
                for source in (item.sources or [])
                if isinstance(source, dict) and str(source.get("content_id", "")).isdigit()
            )

    wants_another = bool(current_tokens.intersection({"outra", "outro", "diferente", "alternativa"}))

    matches: list[tuple[float, Content]] = []
    for content in contents:
        content_tokens = _tokens(
            f"{content.title} {content.description} {content.domain} {content.category}"
        )
        score = len(current_tokens.intersection(content_tokens)) * 3.0
        score += len(context_tokens.intersection(content_tokens)) * 0.35
        if content.domain in requested_domains:
            score += 5.0
        if content.domain in preferred_domains:
            score += 1.2
        normalized_title = _normalize(content.title)
        if normalized_title in _normalize(message):
            score += 10.0
        for mood in requested_moods:
            score += len(content_tokens.intersection(mood_aliases[mood])) * 2.0
        if wants_another and content.id in recently_suggested:
            score -= 4.0
        matches.append((score, content))

    matches.sort(key=lambda item: (-item[0], item[1].title.lower()))
    positive = [content for score, content in matches if score > 0]
    fallback = [content for _, content in matches if content.domain in preferred_domains]
    return (positive or fallback or [content for _, content in matches])[:4], bool(positive)


def _local_answer(
    message: str,
    selected: list[Content],
    history: list[ChatMessage],
    matched: bool,
) -> str:
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
    wants_another = bool(_tokens(message).intersection({"outra", "outro", "diferente", "alternativa"}))
    if wants_another:
        prefix = "Claro — buscando uma opção diferente, "
    elif follow_up:
        prefix = "Considerando também nossa conversa, "
    elif not matched:
        prefix = "Não encontrei uma correspondência exata, mas considerando seus interesses, "
    else:
        prefix = ""
    answer = (
        f"{prefix}minha principal indicação é {primary.title}. "
        f"É um conteúdo de {primary.category.lower()}: {primary.description}"
    )
    if alternatives:
        answer += f" Como alternativas, veja também {alternatives}."
    answer += " Você prefere manter esse estilo ou quer uma alternativa diferente?"
    return answer

async def _online_answer(
    message: str,
    contents: list[Content],
    history: list[ChatMessage],
) -> str | None:
    catalog = [
        {
            "id": content.id,
            "titulo": content.title,
            "dominio": content.domain,
            "categoria": content.category,
            "descricao": content.description[:500],
        }
        for content in contents[:50]
    ]

    conversation = [
        {
            "papel": chat.role,
            "mensagem": chat.message,
        }
        for chat in history[-12:]
    ]

    prompt = f"""
Você é o assistente do Sistema de Recomendação Multidomínio.

Converse de forma natural, educada e objetiva em português do Brasil.

Você pode:

- cumprimentar o usuário;
- responder dúvidas sobre o funcionamento do sistema;
- recomendar filmes, músicas, livros, cursos e produtos;
- comparar conteúdos;
- explicar por que determinado conteúdo foi recomendado;
- considerar o histórico recente da conversa.

Quando fizer recomendações relacionadas ao catálogo:

1. Use somente conteúdos presentes no catálogo enviado.
2. Não invente títulos que não existem no catálogo.
3. Cite no máximo três conteúdos por resposta.
4. Explique resumidamente o motivo de cada indicação.
5. Se não houver conteúdo adequado, avise claramente.

Catálogo disponível:

{json.dumps(catalog, ensure_ascii=False, indent=2)}

Histórico recente:

{json.dumps(conversation, ensure_ascii=False, indent=2)}

Mensagem atual do usuário:

{message}
""".strip()

    return await generate_assistant_answer(prompt)

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
    small_talk = _small_talk_answer(payload.message, user.name)
    selected: list[Content] = []
    matched = False
    if small_talk:
        answer = small_talk
        provider = "local"
    else:
        selected, matched = _score_contents(
            payload.message, contents, history, preferred_domains
        )
        answer = await _online_answer(payload.message, contents, history)
        provider = "online" if answer else "local"
        if not answer:
            answer = _local_answer(payload.message, selected, history, matched)

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
