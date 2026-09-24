from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.dependencies import get_current_user
from app.models import PasswordResetToken, User, UserPreference, UserSession
from app.schemas import (
    AuthResponse,
    LoginRequest,
    PasswordRecoveryRequest,
    PasswordRecoveryResponse,
    PasswordResetRequest,
    ProfileUpdate,
    UserCreate,
    UserPublic,
)


router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.session_days * 24 * 60 * 60,
        path="/",
    )


async def _create_session(db: AsyncSession, user_id: int) -> str:
    token = generate_token()
    now = datetime.now(timezone.utc)
    db.add(
        UserSession(
            user_id=user_id,
            token_hash=hash_token(token),
            created_at=now,
            last_used_at=now,
            expires_at=now + timedelta(days=settings.session_days),
        )
    )
    await db.commit()
    return token


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    email = payload.email.lower().strip()
    existing = await db.scalar(select(User.id).where(User.email == email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este e-mail já está cadastrado.")

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    preference = UserPreference(user_id=user.id, profile={})
    db.add(preference)
    await db.commit()
    await db.refresh(user)
    user.preference = preference

    token = await _create_session(db, user.id)
    _set_session_cookie(response, token)
    return AuthResponse(
        user=UserPublic.model_validate(user),
        message="Cadastro realizado com sucesso.",
        access_token=token,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    result = await db.execute(
        select(User)
        .options(selectinload(User.preference))
        .where(User.email == payload.email.lower().strip())
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta desativada.")

    token = await _create_session(db, user.id)
    _set_session_cookie(response, token)
    return AuthResponse(
        user=UserPublic.model_validate(user),
        message="Autenticação realizada com sucesso.",
        access_token=token,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    token = request.cookies.get("session_token")
    authorization = request.headers.get("authorization", "")
    if not token and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if token:
        await db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(token)))
        await db.commit()
    response.delete_cookie("session_token", path="/")
    return {"message": "Logout realizado com sucesso."}


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(user)


@router.patch("/me", response_model=UserPublic)
async def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    allowed_avatars = {
        "astronauta",
        "robo",
        "coruja",
        "panda",
        "raposa",
        "gato",
        "mago",
        "estrela",
    }
    values = payload.model_dump(exclude_unset=True)
    if values.get("avatar") not in allowed_avatars and "avatar" in values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Escolha um dos avatares disponíveis.",
        )
    if "name" in values:
        values["name"] = values["name"].strip()
    for field, value in values.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return UserPublic.model_validate(user)


@router.post("/recover", response_model=PasswordRecoveryResponse)
async def recover_password(
    payload: PasswordRecoveryRequest,
    db: AsyncSession = Depends(get_db),
) -> PasswordRecoveryResponse:
    user = await db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    response = PasswordRecoveryResponse(
        message="Se o e-mail existir, uma recuperação foi gerada."
    )
    if user is None:
        return response

    token = generate_token()
    now = datetime.now(timezone.utc)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(minutes=settings.reset_token_minutes),
        )
    )
    await db.commit()
    if settings.is_development:
        response.reset_token = token
    return response


@router.post("/reset")
async def reset_password(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(PasswordResetToken)
        .options(selectinload(PasswordResetToken.user))
        .where(PasswordResetToken.token_hash == hash_token(payload.token))
    )
    reset_token = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    expires_at = reset_token.expires_at if reset_token is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (
        reset_token is None
        or reset_token.used_at is not None
        or expires_at is None
        or expires_at <= now
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado.")

    reset_token.user.password_hash = hash_password(payload.new_password)
    reset_token.used_at = now
    await db.execute(delete(UserSession).where(UserSession.user_id == reset_token.user_id))
    await db.commit()
    return {"message": "Senha alterada com sucesso. Faça login novamente."}
