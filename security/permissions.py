from fastapi import Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user
from database import UserModel, UserGroupEnum


async def check_moder_or_admin(
        current_user: UserModel = Depends(get_current_user),
):

    if current_user.group.name not in ["moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action"
        )

    return current_user


async def check_admin(
        current_user: UserModel = Depends(get_current_user),
):

    if current_user.group.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action"
        )

    return current_user
