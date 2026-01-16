import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from database.engine import get_db
from database.models.movies import MovieModel
from schemas.movies import MovieListResponseSchema

router = APIRouter()


async def check_exists_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.scalar(select(MovieModel).where(MovieModel.id == movie_id))

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )

    return movie


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=20)] = 10,
    db: AsyncSession = Depends(get_db),
):
    movies = await db.scalars(select(MovieModel))

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    count = await db.scalar(select(func.count(MovieModel.id)))

    total_pages = math.ceil(count / per_page)

    response = {
        "movies": movies,
        "prev_page": (
            None
            if page == 1
            else f"/theater/movies/?page={page - 1}&per_page={per_page}"
        ),
        "next_page": (
            None
            if page >= total_pages
            else f"/theater/movies/?page={page + 1}&per_page={per_page}"
        ),
        "total_pages": total_pages,
        "total_items": count,
    }

    return response

