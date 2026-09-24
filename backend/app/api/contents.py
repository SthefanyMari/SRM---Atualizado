from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_optional_user, require_admin
from app.models import Content, ContentDomainRecord, Interaction, User
from app.schemas import ContentCreate, ContentList, ContentPublic, ContentUpdate


router = APIRouter(prefix="/contents", tags=["Conteúdos"])


@router.get("", response_model=ContentList)
async def list_contents(
    q: str | None = None,
    domain: str | None = Query(default=None, max_length=40),
    category: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ContentList:
    filters = [Content.is_published.is_(True)]
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(or_(Content.title.ilike(pattern), Content.description.ilike(pattern)))
    if domain:
        filters.append(Content.domain == domain)
    if category:
        filters.append(Content.category.ilike(f"%{category.strip()}%"))

    total = await db.scalar(select(func.count(Content.id)).where(*filters)) or 0
    result = await db.execute(
        select(Content)
        .where(*filters)
        .order_by(Content.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return ContentList(total=total, items=list(result.scalars().all()))


@router.post("", response_model=ContentPublic, status_code=status.HTTP_201_CREATED)
async def create_content(
    payload: ContentCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Content:
    valid_domain = await db.scalar(
        select(ContentDomainRecord.id).where(
            ContentDomainRecord.code == payload.domain,
            ContentDomainRecord.is_active.is_(True),
        )
    )
    if not valid_domain:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Domínio inválido ou inativo.")
    existing = await db.scalar(
        select(Content.id).where(
            Content.source_name == payload.source_name,
            Content.external_id == payload.external_id,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conteúdo já cadastrado.")
    values = payload.model_dump(mode="json")
    values["extra_data"] = values.pop("metadata")
    content = Content(**values)
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return content


@router.get("/{content_id}", response_model=ContentPublic)
async def content_detail(content_id: int, db: AsyncSession = Depends(get_db)) -> Content:
    content = await db.get(Content, content_id)
    if content is None or not content.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conteúdo não encontrado.")
    return content


@router.patch("/{content_id}", response_model=ContentPublic)
async def update_content(
    content_id: int,
    payload: ContentUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Content:
    content = await db.get(Content, content_id)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conteúdo não encontrado.")
    values = payload.model_dump(exclude_unset=True, mode="json")
    if "domain" in values:
        valid_domain = await db.scalar(
            select(ContentDomainRecord.id).where(
                ContentDomainRecord.code == values["domain"],
                ContentDomainRecord.is_active.is_(True),
            )
        )
        if not valid_domain:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Domínio inválido ou inativo.")
    if "metadata" in values:
        values["extra_data"] = values.pop("metadata")
    for field, value in values.items():
        setattr(content, field, value)
    await db.commit()
    await db.refresh(content)
    return content


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    content = await db.get(Content, content_id)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conteúdo não encontrado.")
    await db.delete(content)
    await db.commit()


@router.post("/{content_id}/view", status_code=status.HTTP_201_CREATED)
async def register_view(
    content_id: int,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    content = await db.get(Content, content_id)
    if content is None or not content.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conteúdo não encontrado.")
    if user is not None:
        db.add(
            Interaction(
                user_id=user.id,
                content_id=content.id,
                interaction_type="view",
                context={"source": "catalog"},
            )
        )
        await db.commit()
    return {"message": "Visualização registrada."}
