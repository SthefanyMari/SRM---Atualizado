from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import User, UserPreference
from app.schemas import PreferencePublic, PreferencesUpdate


router = APIRouter(prefix="/preferences", tags=["Preferências"])


def _public_preference(preference: UserPreference | None) -> PreferencePublic:
    profile = preference.profile if preference else {}
    return PreferencePublic(
        preferred_domains=profile.get("preferred_domains", []),
        preferred_categories=profile.get("preferred_categories", []),
    )


@router.get("", response_model=PreferencePublic)
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreferencePublic:
    preference = await db.scalar(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    return _public_preference(preference)


@router.put("", response_model=PreferencePublic)
async def update_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreferencePublic:
    preference = await db.scalar(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    profile = payload.model_dump(mode="json")
    if preference is None:
        preference = UserPreference(user_id=user.id, profile=profile)
        db.add(preference)
    else:
        preference.profile = profile
    await db.commit()
    await db.refresh(preference)
    return _public_preference(preference)

