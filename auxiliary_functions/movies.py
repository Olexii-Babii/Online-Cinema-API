from typing import Annotated, Optional
from urllib.parse import urlencode

from fastapi import Depends, HTTPException, status, Header
from jose import JWTError, ExpiredSignatureError
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.dependencies import get_jwt_auth_manager
from database import MovieModel, StarModel, DirectorModel, GenreModel, UserModel
from database.engine import get_db
from managing.jwt_manager import JWTAuthManager
from schemas.movies import MovieFilterSchema


async def filtering_movie(query: Select, filters: MovieFilterSchema):
    need_distinct = False

    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.where(
            or_(
                MovieModel.name.ilike(search_term),
                MovieModel.description.ilike(search_term),
                MovieModel.stars.any(StarModel.name.ilike(search_term)),
                MovieModel.directors.any(DirectorModel.name.ilike(search_term))
            )
        )

    if filters.genres:
        genres = [int(genre.strip()) for genre in filters.genres.split(",")]
        query = query.join(MovieModel.genres).where(
            GenreModel.id.in_(genres)
    )
        need_distinct = True

    if filters.year:
        query = query.where(MovieModel.year == filters.year)
    else:
        if filters.year_from:
            query = query.where(MovieModel.year >= filters.year_from)
        if filters.year_to:
            query = query.where(MovieModel.year <= filters.year_to)


    if filters.imdb_min:
        query = query.where(MovieModel.imdb >= filters.imdb_min)
    if filters.imdb_max:
        query = query.where(MovieModel.imdb <= filters.imdb_max)


    if filters.director:
        query = query.join(MovieModel.directors).where(
            DirectorModel.name.ilike(f"%{filters.director}%")
        )
        need_distinct = True


    if filters.star:
        query = query.join(MovieModel.stars).where(
            StarModel.name.ilike(f"%{filters.star}%")
        )
        need_distinct = True


    if filters.price_min:
        query = query.where(MovieModel.price >= filters.price_min)
    if filters.price_max:
        query = query.where(MovieModel.price <= filters.price_max)

    if need_distinct:
        query = query.distinct()

    return query


async def sorting_movie(query: Select, filters: MovieFilterSchema):
    sort_mapping = {
        "name": MovieModel.name,
        "year": MovieModel.year,
        "imdb": MovieModel.imdb,
        "price": MovieModel.price,
    }

    sort_column = sort_mapping.get(filters.sort_by.value, MovieModel.id)

    if filters.order.value == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    return query


async def check_exists_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.scalar(select(MovieModel).where(MovieModel.id == movie_id))

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )

    return movie


def build_url(
        filters: MovieFilterSchema,
        page: int,
        per_page: int
):
    filters = filters.model_dump(exclude_none=True, mode="json")
    filters["page"] = page
    filters["per_page"] = per_page
    return f"/movies/?{urlencode(filters)}"


async def check_exists_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    genre = await db.scalar(select(GenreModel).where(GenreModel.id == genre_id))

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre with the given ID was not found.",
        )

    return genre


async def check_exists_star(star_id: int, db: AsyncSession = Depends(get_db)):
    star = await db.scalar(select(StarModel).where(StarModel.id == star_id))

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star with the given ID was not found.",
        )

    return star


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

    db_user = await db.scalar(select(UserModel)
                              .options(selectinload(UserModel.group))
                              .where(UserModel.id == token_user_id))

    return db_user