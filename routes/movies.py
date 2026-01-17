import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from database.engine import get_db
from database.models.movies import MovieModel, GenreModel, StarModel, DirectorModel, CertificationModel
from schemas.movies import MovieListResponseSchema, MovieDetailSchema, MovieCreateSchema

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


@router.post(
    "/movies/", response_model=MovieDetailSchema, status_code=status.HTTP_201_CREATED
)
async def create_movie(movie: MovieCreateSchema, db: AsyncSession = Depends(get_db)):
    db_movie = await db.scalar(select(MovieModel).where(
        MovieModel.name == movie.name,
            MovieModel.time == movie.time,
            MovieModel.year == movie.year
        )
    )
    if db_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{db_movie.name}', time '{db_movie.time}' and release year '{db_movie.year}' already exists.",
        )

    list_models_names = [movie.genres, movie.stars, movie.directors]
    list_models = [GenreModel, StarModel, DirectorModel]
    result_list = []
    for list_names, model in zip(list_models_names, list_models):
        existing_objects = await db.scalars(
            select(model).where(model.name.in_(list_names))
        )
        existing_objects = list(existing_objects)
        if len(existing_objects) != len(list_names):
            existing_names = {g.name for g in existing_objects}
            new_names_to_create = [
                name for name in list_names if name not in existing_names
            ]
            new_objects = []
            for name in new_names_to_create:
                object_ = model(name=name)
                db.add(object_)
                new_objects.append(object_)

            await db.flush()
            result_list.append(existing_objects + new_objects)
        else:
            result_list.append(existing_objects)

    certification = await db.scalar(
        select(CertificationModel).where(CertificationModel.name == movie.certification)
    )

    if not certification:
        certification = CertificationModel(
            name=movie.certification,
        )
        db.add(certification)
        await db.flush()


    new_movie = MovieModel(
        name=movie.name,
        year=movie.year,
        time=movie.time,
        imdb=movie.imdb,
        votes=movie.votes,
        meta_score=movie.meta_score,
        gross=movie.gross,
        description=movie.description,
        price=movie.price,
        certification=certification,
        genres=result_list[0],
        stars=result_list[1],
        directors=result_list[2],
    )

    db.add(new_movie)
    await db.commit()
    await db.refresh(
        new_movie, attribute_names=["genres", "stars", "directors", "certification"]
    )

    return new_movie
