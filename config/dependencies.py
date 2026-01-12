from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from jose import ExpiredSignatureError, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from database import UserModel
from database.engine import get_db
from managing.jwt_manager import JWTAuthManager
from managing.s3_manager import S3Client


def get_settings():
    return Settings()


def get_jwt_auth_manager(settings: Settings = Depends(get_settings)) -> JWTAuthManager:
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )

def get_s3_client(settings: Settings = Depends(get_settings)):
    return S3Client(settings)

async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    jwt_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
    db: AsyncSession = Depends(get_db),
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )

    try:
        payload = jwt_manager.decode_access_token(authorization.split(" ")[1])

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired."
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
        )


    token_user_id = payload.get("user_id")

    db_user = await db.scalar(select(UserModel).where(UserModel.id == token_user_id))

    return db_user
