from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    allowed_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://platform:platform@localhost:5432/platform"
    event_timezone: str = "event-local"
    session_secret: str = "phase0-development-secret-change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
