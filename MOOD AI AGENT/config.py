from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application Settings
    app_name: str = "MOOD AI Agent"
    debug: bool = False
    api_version: str = "v1"
    
    # Database Configuration
    postgres_user: str = "moodz_user"
    postgres_password: str = "moodz_password"
    postgres_db: str = "moodz_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    
    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    
    # Pinecone Configuration
    pinecone_api_key: str
    pinecone_environment: str
    pinecone_index_name: str = "moodz-embeddings"
    
    # CORS Settings
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def cors_origins(self) -> list[str]:
        """Convert comma-separated origins to list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


# Global settings instance
settings = Settings()
