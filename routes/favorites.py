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
    sorting_movie,
)

from auxiliary_functions.movies import get_current_user
from database import UserModel, FavoriteModel
from database import get_db
from database.models.movies import MovieModel

from schemas.favorites import FavoriteMovieResponseSchema
from schemas.movies import MovieListResponseSchema, MovieFilterSchema

router = APIRouter()


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    summary="Get a paginated list of favorite movies",
    description=(
        "<h3>This endpoint retrieves a paginated list of favorite movies from the database. "
        "Clients can specify the `page` number and the number of items per page using `per_page`. "
        "The response includes details about the movies, total pages, and total items, "
        "along with links to the previous and next pages if applicable.\n"
        "The user also has the ability to:\n"
        "1. Search for movies by:\n"
        "- `Title`\n"
        "- `Description`\n"
        "- `Stars`\n"
        "- `Directors`\n"
        "2. Filter movies by:\n"
        "- `Genres`\n"
        "- `Year`\n"
        "- `Year range`\n"
        "- `IMDB range`\n"
        "- `Directors`\n"
        "- `Stars`\n"
        "- `Minimum and maximum price`\n"
        "3. Sort movies by:\n"
        "- `id`\n"
        "- `Title`\n"
        "- `Year`\n"
        "- `IMDB`\n"
        "- `Price`\n"
        "4. Set order (asc or desc)</h3>"
    ),
    responses={
        404: {
            "description": "No movies found.",
            "content": {
                "application/json": {
                    "examples": {
                        "favorite list not found": {
                            "summary": "Favorite list not found",
                            "value": {"detail": "You don't have favorite movies."},
                        },
                        "empty favorite list": {
                            "summary": "Favorite list is empty",
                            "value": {"detail": "Your favorite movies list is empty."},
                        },
                        "no movies found": {
                            "summary": "No movies with given parameters",
                            "value": {"detail": "No movies found."},
                        },
                    }
                }
            },
        }
    },
)
async def get_favorite_movies(
    filters: MovieFilterSchema = Depends(),
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=20)] = 10,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    favorite = await db.scalar(
        select(FavoriteModel)
        .options(selectinload(FavoriteModel.movies))
        .where(FavoriteModel.user_id == current_user.id)
    )

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have favorite movies.",
        )
    movies_ids = [movie.id for movie in favorite.movies]

    if len(movies_ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Your favorite movies list is empty.",
        )

    query = select(MovieModel).where(MovieModel.id.in_(movies_ids))

    query = await filtering_movie(query=query, filters=filters)

    count_query = select(func.count()).select_from(query.subquery())
    count = await db.scalar(count_query)

    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No movies found."
        )

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
            else build_url(filters=filters, per_page=per_page, page=page - 1)
        ),
        "next_page": (
            None
            if page >= total_pages
            else build_url(filters=filters, per_page=per_page, page=page + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }

    return response


@router.post(
    "/{movie_id}/",
    response_model=FavoriteMovieResponseSchema,
    summary="Add the movie to the favorite list.",
    description=(
        "<h3>This endpoint allows clients to add the movie to the favorite list.</h3>"
    ),
    responses={
        409: {
            "description": "Movie already in favorites.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie already in favorites."}
                }
            },
        },
        500: {
            "description": "An error occurred while adding the movie to favorites.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while adding the movie to favorites."
                    }
                }
            },
        },
    },
)
async def add_favorite_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    movie = await check_exists_movie(movie_id=movie_id, db=db)

    favorite = await db.scalar(
        select(FavoriteModel)
        .options(selectinload(FavoriteModel.movies))
        .where(FavoriteModel.user_id == current_user.id)
    )

    try:
        if not favorite:
            favorite = FavoriteModel(user_id=current_user.id, movies=[movie])
            db.add(favorite)

        else:
            if movie in favorite.movies:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Movie already in favorites.",
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
            detail="An error occurred while adding the movie to favorites.",
        )


@router.delete(
    "/{movie_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove the movie from the favorite list.",
    description=(
        "<h3>This endpoint allows clients to remove the movie from the favorite list.</h3>"
    ),
    responses={
        404: {
            "description": "You don't have favorite movies.",
            "content": {
                "application/json": {
                    "example": {"detail": "You don't have favorite movies."}
                }
            },
        },
        409: {
            "description": "Movie is not in favorites.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie is not in favorites."}
                }
            },
        },
        500: {
            "description": "An error occurred while removing the movie from favorites.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while removing the movie from favorites."
                    }
                }
            },
        },
    },
)
async def remove_favorite_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    movie = await check_exists_movie(movie_id=movie_id, db=db)

    favorite = await db.scalar(
        select(FavoriteModel)
        .options(selectinload(FavoriteModel.movies))
        .where(FavoriteModel.user_id == current_user.id)
    )

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have favorite movies.",
        )

    if movie not in favorite.movies:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Movie is not in favorites."
        )

    try:
        favorite.movies.remove(movie)
        await db.commit()

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing the movie from favorites.",
        )
