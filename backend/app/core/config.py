from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ==================================================
    # Application
    # ==================================================
    APP_NAME: str = "ControlPlane API"
    APP_ENV: str = "development"
    DEBUG: bool = True 
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    MAX_COMPLETION_TOKENS: int = 1000
    REDIS_URL: str | None = None

    # ==================================================
    # Database
    # ==================================================
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/controlplane"

    # ==================================================
    # Auth / JWT
    # ==================================================
    JWT_SECRET_KEY: str = "dev-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    DEFAULT_MONTHLY_BUDGET_USD: float = 25.0

    # ==================================================
    # CORS
    # ==================================================
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # ==================================================
    # Pydantic Settings
    # ==================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    ) 

settings = Settings()