from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import hash_token
from app.models import User, UserSession


bearer_scheme = HTTPBearer(auto_error=False)


def _raw_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    return request.cookies.get("session_token")


async def _resolve_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
    *,
    required: bool,
) -> User | None:
    raw_token = _raw_token(request, credentials)
    if not raw_token:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faça login.")
        return None

    result = await db.execute(
        select(UserSession)
        .options(selectinload(UserSession.user).selectinload(User.preference))
        .where(UserSession.token_hash == hash_token(raw_token))
    )
    session = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at if session is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if session is None or expires_at is None or expires_at <= now:
        if session is not None:
            await db.delete(session)
            await db.commit()
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada.")
        return None

    if not session.user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta desativada.")

    session.last_used_at = now
    await db.commit()
    return session.user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _resolve_user(request, credentials, db, required=True)
    assert user is not None
    return user


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    return await _resolve_user(request, credentials, db, required=False)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao administrador.")
    return user
