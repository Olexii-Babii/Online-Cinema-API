from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from auxiliary_functions.movies import check_exists_genre, get_current_user
from database import UserModel, GenreModel, MovieModel
from database import get_db
from database.models.movies import MoviesGenresModel
from schemas.genres import GenresCountResponseSchema, GenresRequestSchema
from schemas.movies import GenresResponseSchema
from security.permissions import check_moder_or_admin

router = APIRouter()


@router.get(
    "/",
    response_model=List[GenresCountResponseSchema],
    summary="Get list of genres with amount of count.",
    description=(
        "<h3>This endpoint allows users to get list of genre with amount of count.</h3>"
    ),
    responses={
        404: {
            "description": "No stars found.",
            "content": {"application/json": {"example": {"detail": "No stars found."}}},
        },
    },
)
async def get_genres(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    genres = await db.execute(
        select(GenreModel.name, func.count(MovieModel.id).label("movie_count"))
        .outerjoin(GenreModel.movies)
        .group_by(GenreModel.id)
    )
    genres = genres.mappings().all()

    return genres


@router.post(
    "/",
    response_model=GenresResponseSchema,
    status_code=status.HTTP_201_CREATED,
    description=(
        "<h3>This endpoint allows moderators or admins to create new genre.</h3>"
    ),
    responses={
        409: {
            "description": "Genre already exists.",
            "content": {
                "application/json": {"example": {"detail": "Genre already exists."}}
            },
        },
        500: {
            "description": "An error occurred while creating the genre.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while creating the genre."}
                }
            },
        },
    },
)
async def create_genre(
    data: GenresRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(check_moder_or_admin),
):
    db_genre = await db.scalar(select(GenreModel).where(GenreModel.name == data.name))

    if db_genre:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Genre already exists."
        )

    try:

        new_genre = GenreModel(name=data.name)
        db.add(new_genre)
        await db.commit()
        await db.refresh(new_genre)

        return new_genre

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the genre.",
        )


@router.patch(
    "/{genre_id}/",
    response_model=GenresResponseSchema,
    description=(
        "<h3>This endpoint allows moderators or admins to update existing genre.</h3>"
    ),
    responses={
        404: {
            "description": "Genre with the given ID was not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Genre with the given ID was not found."}
                }
            },
        },
        409: {
            "description": "Genre with this name ({data.name}) already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre with this name ({data.name}) already exists."
                    }
                }
            },
        },
        500: {
            "description": "An error occurred while updating the genre.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while updating the genre."}
                }
            },
        },
    },
)
async def update_genre(
    genre_id: int,
    data: GenresRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(check_moder_or_admin),
):
    db_genre = await check_exists_genre(genre_id=genre_id, db=db)

    genre_with_same_name = await db.scalar(
        select(GenreModel).where(
            GenreModel.name == data.name, GenreModel.id != genre_id
        )
    )

    if genre_with_same_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Genre with this name ({data.name}) already exists.",
        )

    try:
        db_genre.name = data.name

        await db.commit()
        await db.refresh(db_genre)

        return db_genre

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the genre.",
        )


@router.delete(
    "/{genre_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    description=(
        "<h3>This endpoint allows moderators or admins to delete existing genre. "
        "If there is movie with genre in database, genre can't be deleted.</h3>"
    ),
    responses={
        404: {
            "description": "Genre with the given ID was not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Genre with the given ID was not found."}
                }
            },
        },
        409: {
            "description": "There are already films with this genre.",
            "content": {
                "application/json": {
                    "example": {"detail": "There are already films with this genre."}
                }
            },
        },
        500: {
            "description": "An error occurred while deleting the genre.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while deleting the genre."}
                }
            },
        },
    },
)
async def delete_genre(
    genre_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(check_moder_or_admin),
):
    await check_exists_genre(genre_id=genre_id, db=db)

    movies_count = await db.scalar(
        select(func.count())
        .select_from(MoviesGenresModel)
        .where(MoviesGenresModel.c.genre_id == genre_id)
    )
    if movies_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There are already films with this genre.",
        )

    try:
        await db.execute(delete(GenreModel).where(GenreModel.id == genre_id))
        await db.commit()

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the genre.",
        )
