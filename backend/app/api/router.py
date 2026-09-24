from fastapi import APIRouter

from app.api import admin, assistant, auth, contents, domains, health, interactions, preferences, recommendations


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/api/v1")
api_router.include_router(contents.router, prefix="/api/v1")
api_router.include_router(domains.router, prefix="/api/v1")
api_router.include_router(interactions.router, prefix="/api/v1")
api_router.include_router(preferences.router, prefix="/api/v1")
api_router.include_router(recommendations.router, prefix="/api/v1")
api_router.include_router(assistant.router, prefix="/api/v1")
api_router.include_router(admin.router, prefix="/api/v1")
api_router.include_router(health.router)
