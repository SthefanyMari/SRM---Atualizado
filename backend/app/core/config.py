from functools import lru_cache

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Sistema de Recomendação Multidomínio"
    app_environment: str = "development"
    database_url: str = (
        "postgresql+asyncpg://recomendacao_app:SenhaLocal123@db:5432/recomendacao"
    )
    frontend_origin: str = "http://localhost:3000"
    secure_cookies: bool = False
    session_days: int = 7
    reset_token_minutes: int = 30
    
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"

    admin_name: str = "Administrador"
    admin_email: EmailStr = "admin@recomenda.com"
    admin_password: str = "Admin123@"
    demo_user_name: str = "Usuário de Teste"
    demo_user_email: EmailStr = "usuario@teste.com"
    demo_user_password: str = "Teste123@"

    @property
    def is_development(self) -> bool:
        return self.app_environment.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
