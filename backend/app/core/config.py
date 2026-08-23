from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ==================================================
    # Application
    # ==================================================
    APP_NAME: str = "ControlPlane API"
    APP_ENV: str = "development"
    DEBUG: bool = True 

    # ==================================================
    # Database
    # ==================================================
    DATABASE_URL: str

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