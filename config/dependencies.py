import os

from fastapi import Depends

from config.settings import Settings, TestingSettings
from managing.jwt_manager import JWTAuthManager
from managing.s3_manager import S3Client


def get_settings():
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return Settings()


def get_jwt_auth_manager(settings: Settings = Depends(get_settings)) -> JWTAuthManager:
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )

def get_s3_client(settings: Settings = Depends(get_settings)):
    return S3Client(settings)


