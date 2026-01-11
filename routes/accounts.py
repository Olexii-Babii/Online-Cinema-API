from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database import UserModel, ActivationTokenModel, UserGroupModel, PasswordResetTokenModel
from database.engine import get_db
from email_notification.email_sender import EmailSender
from schemas import accounts as schemas

from typing import cast

router = APIRouter()
email_sender = EmailSender()

@router.post("/register/",
             response_model=schemas.UserRegistrationResponseSchema,
             status_code=status.HTTP_201_CREATED)
async def register_user(user: schemas.UserRegistrationRequestSchema,
                        background_tasks: BackgroundTasks,
                        db: AsyncSession = Depends(get_db)):
    db_user = await db.scalar(select(UserModel).where(UserModel.email == user.email))

    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user.email} already exists."
        )
    db_group = await db.scalar(select(UserGroupModel).where(UserGroupModel.name == "user"))

    if not db_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found."
        )

    try:
        new_user = UserModel(
            email=user.email,
            password=user.password,
            group_id=db_group.id
        )
        db.add(new_user)
        await db.flush()
        activation_token = ActivationTokenModel(
            user_id=new_user.id,
        )
        db.add(activation_token)
        await db.flush()
        # background_tasks.add_task(email_sender.send_activation_email, activation_token.token, user.email)

        await db.commit()
        await db.refresh(new_user)
        return new_user

    except SQLAlchemyError as e:
        print(f"Error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation.",
        )


@router.post("/activate/", response_model=schemas.MessageResponseSchema)
async def activate_user(
        background_tasks: BackgroundTasks,
        data: schemas.UserActivationRequestSchema,
        db: AsyncSession = Depends(get_db)
):

    db_user = await db.scalar(select(UserModel).where(UserModel.email == data.email))
    db_token = await db.scalar(select(ActivationTokenModel).where(ActivationTokenModel.token == data.token))

    if db_token:
        expires_at = cast(datetime, db_token.expires_at).replace(tzinfo=timezone.utc)

    if (
            not db_user
            or not db_token
            or db_token.user_id != db_user.id
            or datetime.now(timezone.utc) > expires_at
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token.",
        )

    elif db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )

    try:
        db_user.is_active = True

        await db.execute(delete(ActivationTokenModel).where(ActivationTokenModel.user_id == db_user.id))
        # background_tasks.add_task(email_sender.send_activation_complete_email, db_user.email)
        await db.commit()

        return {"message": "User account activated successfully."}

    except SQLAlchemyError as e:
        print(f"Error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during activation.",
        )

@router.post("/resend-activation/", response_model=schemas.MessageResponseSchema)
async def resend_activation_email(
        background_tasks: BackgroundTasks,
        data: schemas.EmailRequestSchema,
        db: AsyncSession = Depends(get_db)
):
    db_user = await db.scalar(select(UserModel).where(UserModel.email == data.email))

    if not db_user:
        return {"message": "If the user exists, you will receive a token"}

    if db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )
    db_token = await db.scalar(select(ActivationTokenModel).where(ActivationTokenModel.user_id == db_user.id))

    if db_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is already exists.",
        )

    try:
        activation_token = ActivationTokenModel(
            user_id=db_user.id,
        )
        db.add(activation_token)
        await db.flush()
        # background_tasks.add_task(email_sender.send_activation_email, activation_token.token, db_user.email)

        await db.commit()

        return {"message": "If the user exists, you will receive a token"}

    except SQLAlchemyError as e:
        print(f"Error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token creation.",
        )



@router.post("/password-reset/request/", response_model=schemas.MessageResponseSchema)
async def password_reset_request(
        data: schemas.EmailRequestSchema,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db)
):
    db_user = await db.scalar(select(UserModel).where(UserModel.email == data.email))

    if not db_user or not db_user.is_active:
        return {
            "message": "If you are registered, you will receive an email with instructions."
        }
    try:
        await db.execute(
            delete(PasswordResetTokenModel).where(
                PasswordResetTokenModel.user_id == db_user.id
            )
        )
        token = PasswordResetTokenModel(user_id=db_user.id)
        db.add(token)
        await db.flush()
        # background_tasks.add_task(email_sender.send_password_reset_email, email_to=db_user.email, token=token.token)
        await db.commit()

        return {
            "message": "If you are registered, you will receive an email with instructions."
        }

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password reset request.",
        )


@router.post("/reset-password/complete/", response_model=schemas.MessageResponseSchema)
async def reset_password_complete(
        data: schemas.PasswordResetCompleteRequestSchema,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
):

    db_user = await db.scalar(select(UserModel).where(UserModel.email == data.email))
    db_token = await db.scalar(select(PasswordResetTokenModel).where(PasswordResetTokenModel.token == data.token))

    if not db_user or not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    if db_token:
        expires_at = cast(datetime, db_token.expires_at).replace(tzinfo=timezone.utc)

    if (
        not db_token
        or db_user.id != db_token.user_id
        or expires_at <= datetime.now(timezone.utc)
    ):
        await db.execute(
            delete(PasswordResetTokenModel).where(
                PasswordResetTokenModel.user_id == db_user.id
            )
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    try:
        db_user.password = data.password
        await db.execute(
            delete(PasswordResetTokenModel).where(
                PasswordResetTokenModel.user_id == db_user.id
            )
        )
        await db.commit()
        return {"message": "Password reset successfully."}

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password.",
        )
