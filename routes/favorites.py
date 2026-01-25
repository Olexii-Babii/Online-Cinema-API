import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auxiliary_functions.movies import (
    build_url,
    check_exists_movie,
    filtering_movie,
    sorting_movie
)

from auxiliary_functions.movies import get_current_user
from database import UserModel,  FavoriteModel
from database.engine import get_db
from database.models.movies import MovieModel

from schemas.favorites import FavoriteMovieResponseSchema
from schemas.movies import (
    MovieListResponseSchema,
    MovieFilterSchema
)


router = APIRouter()


@router.get("/", response_model=MovieListResponseSchema)
async def get_favorite_movies(
    filters: MovieFilterSchema = Depends(),
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=20)] = 10,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    favorite = await db.scalar(select(FavoriteModel)
                               .options(selectinload(FavoriteModel.movies))
                               .where(FavoriteModel.user_id == current_user.id)
                               )

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have favorite movies."
        )
    movies_ids = [movie.id for movie in favorite.movies]

    if len(movies_ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Your favorite movies list is empty."
        )

    query = select(MovieModel).where(MovieModel.id.in_(movies_ids))

    query = await filtering_movie(query=query, filters=filters)

    count_query = select(func.count()).select_from(query.subquery())
    count = await db.scalar(count_query)

    if count == 0:
        raise HTTPException(status_code=404, detail="No movies found.")

    query = await sorting_movie(query=query, filters=filters)

    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    movies = result.scalars().all()

    total_pages = math.ceil(count / per_page)

    response = {
        "movies": movies,
        "prev_page": (
            None
            if page == 1
            else build_url(filters=filters, per_page=per_page, page=page-1)
        ),
        "next_page": (
            None
            if page >= total_pages
            else build_url(filters=filters, per_page=per_page, page=page+1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }

    return response


@router.post("/{movie_id}/", response_model=FavoriteMovieResponseSchema)
async def add_favorite_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user),
):
    movie = await check_exists_movie(movie_id=movie_id, db=db)

    favorite = await db.scalar(select(FavoriteModel)
                               .options(selectinload(FavoriteModel.movies))
                               .where(FavoriteModel.user_id == current_user.id)
                               )

    try:
        if not favorite:
            favorite = FavoriteModel(
                user_id=current_user.id,
                movies=[movie]
            )
            db.add(favorite)

        else:
            if movie in favorite.movies:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Movie already in favorites."
                )
            favorite.movies.append(movie)

        await db.commit()

        return {
            "movie_id": movie_id,
            "message": "You successfully added your favorite movie.",
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding the movie to favorites."
        )


@router.delete("/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user),
):
    movie = await check_exists_movie(movie_id=movie_id, db=db)

    favorite = await db.scalar(select(FavoriteModel)
                               .options(selectinload(FavoriteModel.movies))
                               .where(FavoriteModel.user_id == current_user.id)
                               )

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have favorite movies."
        )

    if movie not in favorite.movies:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie is not in favorites."
        )

    try:
        favorite.movies.remove(movie)
        await db.commit()

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing the movie from favorites."
        )