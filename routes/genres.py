from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.dependencies import get_current_user
from database import UserModel, GenreModel, MovieModel
from database.engine import get_db
from schemas.genres import GenresCountResponseSchema

router = APIRouter()


@router.get("/", response_model=List[GenresCountResponseSchema])
async def get_genres(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    genres = await db.execute(select(GenreModel.name, func.count(MovieModel.id).label("movie_count"))
                              .outerjoin(GenreModel.movies)
                              .group_by(GenreModel.id))
    genres = genres.mappings().all()

    return genres




