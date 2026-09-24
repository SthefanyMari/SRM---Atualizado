from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import ContentDomainRecord
from app.schemas import DomainPublic


router = APIRouter(prefix="/domains", tags=["Domínios"])


@router.get("", response_model=list[DomainPublic])
async def list_domains(db: AsyncSession = Depends(get_db)) -> list[ContentDomainRecord]:
    result = await db.execute(
        select(ContentDomainRecord)
        .where(ContentDomainRecord.is_active.is_(True))
        .order_by(ContentDomainRecord.name)
    )
    return list(result.scalars().all())
