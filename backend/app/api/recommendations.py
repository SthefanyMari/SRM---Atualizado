from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import (
    Content,
    Interaction,
    RecommendationFeedback,
    User,
    UserPreference,
)
from app.schemas import (
    FeedbackCreate,
    RecommendationItem,
    RecommendationResponse,
)
from app.services.recommender import rank_contents


router = APIRouter(prefix="/recommendations", tags=["Recomendações"])


@router.get("", response_model=RecommendationResponse)
async def recommendations(
    limit: int = Query(default=10, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    contents_result = await db.execute(
        select(Content).where(Content.is_published.is_(True))
    )
    contents = list(contents_result.scalars().all())
    preference = await db.scalar(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    interactions_result = await db.execute(
        select(Interaction)
        .options(selectinload(Interaction.content))
        .where(Interaction.user_id == user.id)
        .order_by(Interaction.created_at.desc())
        .limit(300)
    )
    interactions = list(interactions_result.scalars().all())
    feedback_result = await db.execute(
        select(RecommendationFeedback)
        .where(RecommendationFeedback.user_id == user.id)
        .order_by(RecommendationFeedback.created_at.asc())
        .limit(300)
    )
    feedbacks = list(feedback_result.scalars().all())
    ranked = rank_contents(contents, preference, interactions, feedbacks)[:limit]

    items = [
        RecommendationItem(content=content, score=score, reason=reason)
        for content, score, reason in ranked
    ]
    for content, score, reason in ranked:
        db.add(
            Interaction(
                user_id=user.id,
                content_id=content.id,
                interaction_type="recommendation",
                value=score,
                context={"reason": reason},
            )
        )
    await db.commit()
    return RecommendationResponse(items=items)


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def recommendation_feedback(
    payload: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if await db.get(Content, payload.content_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conteúdo não encontrado.")
    db.add(
        RecommendationFeedback(
            user_id=user.id,
            content_id=payload.content_id,
            relevant=payload.relevant,
            explanation=payload.explanation,
        )
    )
    await db.commit()
    return {"message": "Obrigado! Seu feedback foi registrado."}
