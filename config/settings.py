import os
from pathlib import Path

from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent
    PATH_TO_DB: str = str(BASE_DIR / "movies.db")

    LOGIN_TIME_DAYS: int = 7


    BASE_URL: str = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "testuser")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "test_password")
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@theater.com")
    MAIL_PORT = os.getenv("MAIL_PORT", 1025)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "mailhog_theater")
    MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", False)
    MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", False)
    USE_CREDENTIALS = os.getenv("USE_CREDENTIALS", True)
    VALIDATE_CERTS = os.getenv("VALIDATE_CERTS", False)

    S3_STORAGE_HOST: str = os.getenv("MINIO_HOST", "minio-theater")
    S3_STORAGE_PORT: int = os.getenv("MINIO_PORT", 9000)
    S3_STORAGE_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    S3_STORAGE_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "some_password")
    S3_BUCKET_NAME: str = os.getenv("MINIO_STORAGE", "theater-storage")

    @property
    def S3_STORAGE_ENDPOINT(self) -> str:
        return f"http://{self.S3_STORAGE_HOST}:{self.S3_STORAGE_PORT}"


class Settings(BaseAppSettings):
    SECRET_KEY_ACCESS: str = os.getenv("SECRET_KEY_ACCESS", os.urandom(32))
    SECRET_KEY_REFRESH: str = os.getenv("SECRET_KEY_REFRESH", os.urandom(32))
    JWT_SIGNING_ALGORITHM: str = os.getenv("JWT_SIGNING_ALGORITHM", "HS256")
