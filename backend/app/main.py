from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import close_database, create_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_tables()
    yield
    await close_database()


app = FastAPI(
    title=settings.app_name,
    description=(
        "API para recomendação semântica multidomínio, interações, "
        "administração e assistente de IA."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "message": settings.app_name,
        "documentation": "/docs",
        "health": "/health",
    }

