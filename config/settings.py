import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent
    PATH_TO_DB: str = str(BASE_DIR / "movies.db")

    LOGIN_TIME_DAYS: int = 7

    BASE_URL: str = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "testuser")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "test_password")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@theater.com")
    MAIL_PORT: int = os.getenv("MAIL_PORT", 1025)
    MAIL_API_PORT: int = os.getenv("MAIL_API_PORT", 8025)
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "mailhog_theater")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", False)
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", False)
    USE_CREDENTIALS: bool = os.getenv("USE_CREDENTIALS", True)
    VALIDATE_CERTS: bool = os.getenv("VALIDATE_CERTS", False)

    S3_STORAGE_HOST: str = os.getenv("MINIO_HOST", "minio-theater")
    S3_STORAGE_PORT: int = os.getenv("MINIO_PORT", 9000)
    S3_STORAGE_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    S3_STORAGE_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "some_password")
    S3_BUCKET_NAME: str = os.getenv("MINIO_STORAGE", "theater-storage")

    @property
    def S3_STORAGE_ENDPOINT(self) -> str:
        return f"http://{self.S3_STORAGE_HOST}:{self.S3_STORAGE_PORT}"


class Settings(BaseAppSettings):
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "test_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "test_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "test_host")
    POSTGRES_DB_PORT: int = int(os.getenv("POSTGRES_DB_PORT", 5432))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "test_db")

    @property
    def SYNC_DATABASE_URL(self):
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB}"

    SECRET_KEY_ACCESS: str = os.getenv("SECRET_KEY_ACCESS", os.urandom(32))
    SECRET_KEY_REFRESH: str = os.getenv("SECRET_KEY_REFRESH", os.urandom(32))
    JWT_SIGNING_ALGORITHM: str = os.getenv("JWT_SIGNING_ALGORITHM", "HS256")
    # PATH_TO_DB: str = os.getenv("PATH_TO_DB", "./movies.db")


class TestingSettings(BaseAppSettings):
    SECRET_KEY_ACCESS: str = "SECRET_KEY_ACCESS"
    SECRET_KEY_REFRESH: str = "SECRET_KEY_REFRESH"
    JWT_SIGNING_ALGORITHM: str = "HS256"

    def model_post_init(self, __context: dict[str, Any] | None = None) -> None:
        object.__setattr__(self, "PATH_TO_DB", ":memory:")
