from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Default values for optional settings. These can be overridden by the .env file or environment variables.
    DATABASE_URL: str = "sqlite:///./automations.db"
    WORKER_IMAGE: str = "opentrack-worker:latest"
    # Required settings without default values. These must be provided in the .env file or as environment variables.
    KUBERNETES_NAMESPACE: str
    KAFKA_BROKERS: str
    THINGS_SERVICE_URL: str
    BENTLOY_SERVICE_URL: str
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()