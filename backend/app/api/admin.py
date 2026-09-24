from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies import require_admin
from app.core.security import hash_password
from app.models import (
    Content,
    ContentDomainRecord,
    Interaction,
    RecommendationFeedback,
    User,
    UserPreference,
)
from app.schemas import (
    AdminUserCreate,
    ContentList,
    DomainCreate,
    DomainPublic,
    DomainUpdate,
    StatisticsResponse,
    UserPublic,
    UserUpdate,
)


router = APIRouter(prefix="/admin", tags=["Administração"])


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.preference))
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    email = payload.email.lower().strip()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este e-mail já está cadastrado.")
    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        is_active=True,
        avatar="astronauta",
    )
    db.add(user)
    await db.flush()
    preference = UserPreference(user_id=user.id, profile={})
    db.add(preference)
    await db.commit()
    await db.refresh(user)
    user.preference = preference
    return user


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(
        select(User).options(selectinload(User.preference)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    for field, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(user, field, value)
    await db.commit()
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O administrador não pode excluir a própria conta.",
        )
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    await db.delete(user)
    await db.commit()


@router.get("/contents", response_model=ContentList)
async def list_all_contents(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ContentList:
    total = await db.scalar(select(func.count(Content.id))) or 0
    result = await db.execute(
        select(Content).order_by(Content.created_at.desc()).offset(offset).limit(limit)
    )
    return ContentList(total=total, items=list(result.scalars().all()))


@router.get("/domains", response_model=list[DomainPublic])
async def list_all_domains(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ContentDomainRecord]:
    result = await db.execute(select(ContentDomainRecord).order_by(ContentDomainRecord.name))
    return list(result.scalars().all())


@router.post("/domains", response_model=DomainPublic, status_code=status.HTTP_201_CREATED)
async def create_domain(
    payload: DomainCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ContentDomainRecord:
    code = payload.code.lower().strip()
    if await db.scalar(select(ContentDomainRecord.id).where(ContentDomainRecord.code == code)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este domínio já está cadastrado.")
    domain = ContentDomainRecord(
        code=code,
        name=payload.name.strip(),
        description=payload.description.strip(),
        is_active=payload.is_active,
    )
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    return domain


@router.patch("/domains/{domain_id}", response_model=DomainPublic)
async def update_domain(
    domain_id: int,
    payload: DomainUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ContentDomainRecord:
    domain = await db.get(ContentDomainRecord, domain_id)
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domínio não encontrado.")
    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(domain, field, value.strip() if isinstance(value, str) else value)
    await db.commit()
    await db.refresh(domain)
    return domain


@router.delete("/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    domain_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    domain = await db.get(ContentDomainRecord, domain_id)
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domínio não encontrado.")
    in_use = await db.scalar(select(func.count(Content.id)).where(Content.domain == domain.code)) or 0
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este domínio possui conteúdos. Exclua ou mova os conteúdos primeiro.",
        )
    await db.delete(domain)
    await db.commit()


@router.get("/statistics", response_model=StatisticsResponse)
async def statistics(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StatisticsResponse:
    users = await db.scalar(select(func.count(User.id))) or 0
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active.is_(True))
    ) or 0
    contents = await db.scalar(select(func.count(Content.id))) or 0
    interactions = await db.scalar(select(func.count(Interaction.id))) or 0
    feedbacks = await db.scalar(select(func.count(RecommendationFeedback.id))) or 0

    domain_result = await db.execute(
        select(Content.domain, func.count(Content.id)).group_by(Content.domain)
    )
    interaction_result = await db.execute(
        select(Interaction.interaction_type, func.count(Interaction.id)).group_by(
            Interaction.interaction_type
        )
    )
    return StatisticsResponse(
        users=users,
        active_users=active_users,
        contents=contents,
        interactions=interactions,
        feedbacks=feedbacks,
        contents_by_domain={domain: count for domain, count in domain_result.all()},
        interactions_by_type={kind: count for kind, count in interaction_result.all()},
    )
