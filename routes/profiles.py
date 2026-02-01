from botocore.exceptions import HTTPClientError, NoCredentialsError, BotoCoreError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import  get_s3_client
from database import UserModel, UserGroupModel, UserProfileModel, UserGroupEnum
from database import get_db
from managing.s3_manager import S3Client
from schemas.profiles import ProfileResponseSchema, ProfileRequestSchema, ProfileBaseSchema
from auxiliary_functions.movies import get_current_user

router = APIRouter()


@router.post(
    "/users/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    summary="Create user profile",
    description="User profile creation",
    status_code=status.HTTP_201_CREATED,
    responses={
                 400: {
                     "description": "Bad Request - User already has a profile.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "User already has a profile."
                             }
                         }
                     },
                 },
                 401: {
                     "description": "Unauthorized - User not found or not active.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "User not found or not active."
                             }
                         }
                     },
                 },
                 403: {
                     "description": "Forbidden - User can not create profile for another user.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "You don't have permission to edit this profile."
                             }
                         }
                     },
                 },
    }
)
async def create_user_profile(
    user_id: int,
    db_user: UserModel = Depends(get_current_user),
    profile: ProfileRequestSchema = Depends(ProfileRequestSchema.as_form),
    s3_client: S3Client = Depends(get_s3_client),
    db: AsyncSession = Depends(get_db),
):

    if not db_user or db_user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active.",
        )

    db_user_group = await db.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.ADMIN)
    )

    if db_user.id != user_id and db_user.group_id != db_user_group.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this profile.",
        )

    db_profile = await db.scalar(
        select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    )

    if db_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile.",
        )

    try:
        file_name = f"avatars/{user_id}_avatar.jpg"
        file_data = await profile.avatar.read()

        await s3_client.upload_image(file_name=file_name, file_data=file_data)

        file_url = await s3_client.get_file_url(file_name=file_name)

        db_profile = UserProfileModel(
            first_name=profile.first_name.lower(),
            last_name=profile.last_name.lower(),
            gender=profile.gender,
            date_of_birth=profile.date_of_birth,
            info=profile.info,
            user_id=user_id,
            avatar=file_name,
        )

        db.add(db_profile)
        await db.commit()
        await db.refresh(db_profile)
        db_profile.avatar = file_url

        return db_profile

    except (
        ConnectionError,
        HTTPClientError,
        NoCredentialsError,
        BotoCoreError
    ):
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later.",
        )

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating profile.",
        )


@router.get("/me",
            response_model=ProfileResponseSchema,
            status_code=status.HTTP_200_OK,
            summary="User`s profile",
            description=("Allows the user to obtain information about themselves"),
            )
async def read_me(current_user: ProfileBaseSchema = Depends(get_current_user),
                  db: AsyncSession = Depends(get_db)):
    return current_user
