from fastapi import Depends

from config.settings import Settings
from managing.jwt_manager import JWTAuthManager

def get_settings():
    return Settings()


def get_jwt_auth_manager(settings: Settings = Depends(get_settings)) -> JWTAuthManager:
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )
