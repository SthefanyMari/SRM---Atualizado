from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Content, Interaction, User
from app.schemas import InteractionCreate, InteractionPublic


router = APIRouter(prefix="/interactions", tags=["Interações"])


@router.post("", response_model=InteractionPublic, status_code=status.HTTP_201_CREATED)
async def register_interaction(
    payload: InteractionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Interaction:
    if await db.get(Content, payload.content_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conteúdo não encontrado.")
    if payload.interaction_type.value == "rating" and (
        payload.value is None or payload.value < 1 or payload.value > 5
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A avaliação deve estar entre 1 e 5.")
    interaction = Interaction(
        user_id=user.id,
        content_id=payload.content_id,
        interaction_type=payload.interaction_type.value,
        value=payload.value,
        context=payload.context,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    return interaction


@router.get("/history", response_model=list[InteractionPublic])
async def interaction_history(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Interaction]:
    result = await db.execute(
        select(Interaction)
        .options(selectinload(Interaction.content))
        .where(Interaction.user_id == user.id)
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
