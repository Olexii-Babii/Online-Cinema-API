from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from jose import JWTError, ExpiredSignatureError
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_jwt_auth_manager
from database import UserModel, ActivationTokenModel, UserGroupModel, PasswordResetTokenModel, RefreshTokenModel
from database.engine import get_db
from email_notification.email_sender import EmailSender
from schemas import accounts as schemas

from typing import cast

from managing.jwt_manager import JWTAuthManager

router = APIRouter()
email_sender = EmailSender()


@router.post("/register/",
             response_model=schemas.UserRegistrationResponseSchema,
             summary="User Registration",
             description="Register a new user with an email and password.",
             status_code=status.HTTP_201_CREATED,
             responses={
                 409: {
                     "description": "Conflict - User with this email already exists.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "A user with this email test@example.com already exists."
                             }
                         }
                     },
                 },
                 500: {
                     "description": "Internal Server Error - An error occurred during user creation.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "An error occurred during user creation."
                             }
                         }
                     },
                 },
             }
             )
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
        background_tasks.add_task(email_sender.send_activation_email, activation_token.token, user.email)

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


@router.post("/activate/",
             response_model=schemas.MessageResponseSchema,
             summary="Activate User Account",
             description="Activate a user's account using their email and activation token.",
             status_code=status.HTTP_200_OK,
             responses={
                 400: {
                     "description": "Bad Request - The activation token is invalid or expired, "
                                    "or the user account is already active.",
                     "content": {
                         "application/json": {
                             "examples": {
                                 "invalid_token": {
                                     "summary": "Invalid Token",
                                     "value": {
                                         "detail": "Invalid or expired activation token."
                                     }
                                 },
                                 "already_active": {
                                     "summary": "Account Already Active",
                                     "value": {
                                         "detail": "User account is already active."
                                     }
                                 },
                             }
                         }
                     },
                 },
                 500: {
                     "description": "Internal Server Error - An error occurred during user activation account.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "An error occurred during activation."
                             }
                         }
                     },
                 },
             },

             )
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
        background_tasks.add_task(email_sender.send_activation_complete_email, db_user.email)
        await db.commit()

        return {"message": "User account activated successfully."}

    except SQLAlchemyError as e:
        print(f"Error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during activation.",
        )


@router.post("/resend-activation/",
             response_model=schemas.MessageResponseSchema,
             summary="Request Resend Activation Token",
             description=(
                     "Allows users to re-obtain an activation token"
             ),
             status_code=status.HTTP_200_OK,
             responses={
                 400: {
                     "description": "Bad Request - The activation token is already exists, "
                                    "or the user account is already active.",
                     "content": {
                         "application/json": {
                             "examples": {
                                 "invalid_token": {
                                     "summary": "Token Already Exists",
                                     "value": {
                                         "detail": "Token is already exists."
                                     }
                                 },
                                 "already_active": {
                                     "summary": "Account Already Active",
                                     "value": {
                                         "detail": "User account is already active."
                                     }
                                 },
                             }
                         }
                     },
                 },
                 500: {
                     "description": "Internal Server Error - An error occurred during creation activation token.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "An error occurred during token creation."
                             }
                         }
                     },
                 },
             },
             )
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
        background_tasks.add_task(email_sender.send_activation_email, activation_token.token, db_user.email)

        await db.commit()

        return {"message": "If the user exists, you will receive a token"}

    except SQLAlchemyError as e:
        print(f"Error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token creation.",
        )


@router.post("/password-reset/request/",
             response_model=schemas.MessageResponseSchema,
             summary="Request Password Reset Token",
             description=(
                     "Allows a user to request a password reset token. If the user exists and is active, "
                     "a new token will be generated and any existing tokens will be invalidated."
             ),
             status_code=status.HTTP_200_OK,
             )
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
        background_tasks.add_task(email_sender.send_password_reset_email, email_to=db_user.email, token=token.token)
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


@router.post("/reset-password/complete/",
             response_model=schemas.MessageResponseSchema,
             summary="Reset User Password",
             description="Reset a user's password if a valid token is provided.",
             status_code=status.HTTP_200_OK,
             responses={
                 400: {
                     "description": (
                             "Bad Request - The provided email or token is invalid, "
                             "the token has expired, or the user account is not active."
                     ),
                     "content": {
                         "application/json": {
                             "examples": {
                                 "invalid_email_or_token": {
                                     "summary": "Invalid Email or Token",
                                     "value": {
                                         "detail": "Invalid email or token."
                                     }
                                 },
                                 "expired_token": {
                                     "summary": "Expired Token",
                                     "value": {
                                         "detail": "Invalid email or token."
                                     }
                                 }
                             }
                         }
                     },
                 },
                 500: {
                     "description": "Internal Server Error - An error occurred while resetting the password.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "An error occurred while resetting the password."
                             }
                         }
                     },
                 },
             },
             )
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
        background_tasks.add_task(email_sender.send_password_reset_complete_email, email_to=db_user.email)
        return {"message": "Password reset successfully."}

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password.",
        )


@router.post("/reset-password-with-old-one/",
             response_model=schemas.MessageResponseSchema,
             summary="Reset User Password With Old One",
             description="Reset a user's password if a valid old password is provided.",
             status_code=status.HTTP_200_OK,
             responses={
                 400: {
                     "description": (
                             "Bad Request - The provided email or password is invalid, "
                             "or the user account is not active."
                     ),
                     "content": {
                         "application/json": {
                             "examples": {
                                 "invalid_email_or_token": {
                                     "summary": "Invalid Email or User is Not Active",
                                     "value": {
                                         "detail": "Invalid email or password, or user is not active."
                                     }
                                 },
                                 "expired_token": {
                                     "summary": "Invalid Password",
                                     "value": {
                                         "detail": "Invalid email or password, or user is not active."
                                     }
                                 }
                             }
                         }
                     },
                 },
                 500: {
                     "description": "Internal Server Error - An error occurred while resetting the password.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "An error occurred while resetting the password."
                             }
                         }
                     },
                 },
             },
             )
async def reset_password_with_old_one(
        data: schemas.PasswordWithOldResetRequestSchema,
        db: AsyncSession = Depends(get_db),
):
    db_user = await db.scalar(select(UserModel).where(UserModel.email == data.email))

    if not db_user or not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password, or user is not active."
        )

    if not db_user.verify_password(data.old_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password, or user is not active."
        )

    try:
        db_user.password = data.new_password
        db.add(db_user)
        await db.commit()
        return {"message": "Password reset successfully."}

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password.",
        )


@router.post(
    "/login/",
    response_model=schemas.UserLoginResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="User Login",
    description="Authenticate a user and return access and refresh tokens.",
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid email or password."
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - User account is not activated.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User account is not activated."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while processing the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing the request."
                    }
                }
            },
        },
    },
)
async def user_login(
    login_data: schemas.UserLoginRequestSchema,
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
):
    db_user = await db.scalar(select(UserModel).where(UserModel.email == login_data.email))

    if (not db_user) or not db_user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    elif not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    try:
        access_token = jwt_manager.create_access_token(
            data={"email": db_user.email, "user_id": db_user.id}
        )
        refresh_token = jwt_manager.create_refresh_token(
            data={"email": db_user.email, "user_id": db_user.id}
        )
        payload_refresh_token = jwt_manager.decode_refresh_token(refresh_token)
        days_valid = payload_refresh_token["exp"] // (60 * 24)
        expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        await db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.user_id == db_user.id))
        db_refresh_token = RefreshTokenModel(
            user_id=db_user.id,
            token=refresh_token,
            expires_at=expires_at,
        )
        db.add(db_refresh_token)
        await db.commit()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )


@router.post("/refresh/",
             response_model=schemas.TokenRefreshResponseSchema,
             summary="Refresh Access Token",
             description="Refresh the access token using a valid refresh token.",
             status_code=status.HTTP_200_OK,
             responses={
                 400: {
                     "description": "Bad Request - The provided refresh token is invalid or expired.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Token has expired."
                             }
                         }
                     },
                 },
                 401: {
                     "description": "Unauthorized - Refresh token not found.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Refresh token not found."
                             }
                         }
                     },
                 },
                 404: {
                     "description": "Not Found - The user associated with the token does not exist.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "User not found."
                             }
                         }
                     },
                 },
             },

             )
async def refresh_access_token(
    refresh_token: schemas.TokenRefreshRequestSchema,
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
):
    try:
        payload = jwt_manager.decode_refresh_token(refresh_token.refresh_token)
    except (JWTError, ExpiredSignatureError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token has expired."
        )

    db_refresh_token = await db.scalar(
        select(RefreshTokenModel).where(
            RefreshTokenModel.token == refresh_token.refresh_token
        )
    )

    if not db_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found."
        )

    db_user = await db.scalar(select(UserModel).where(UserModel.id == db_refresh_token.user_id))

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    elif db_user.id != db_refresh_token.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    access_token = jwt_manager.create_access_token(
        data={"email": db_user.email, "user_id": db_user.id}
    )

    return {"access_token": access_token}


@router.post("/logout/",
             response_model=schemas.MessageResponseSchema,
             status_code=status.HTTP_200_OK,
             summary="User Logout",
             description=("Allows users to log out of their page."),
             )
async def logout(
        data: schemas.LogoutRequestSchema,
        db: AsyncSession = Depends(get_db)
):
    await db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.token == data.refresh_token))
    await db.commit()
    return {"message": "You have been logged out."}
