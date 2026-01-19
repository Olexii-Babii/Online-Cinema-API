import math
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete, or_, Select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.dependencies import get_current_user
from database import UserModel, MovieReactionModel
from database.engine import get_db
from database.models.movies import (
    MovieModel,
    GenreModel,
    StarModel,
    DirectorModel,
    CertificationModel,
    MovieCommentModel
)
from schemas.accounts import MessageResponseSchema
from schemas.movies import (
    MovieListResponseSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
    ReactionRequestSchema,
    CommentRequestSchema,
    CommentResponseSchema,
    CommentReplyResponseSchema,
    CommentReplyRequestSchema,
    MovieFilterSchema
)

router = APIRouter()


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
        genres = [genre.strip() for genre in filters.genres.split(",")]
        query = query.join(MovieModel.genres).where(
            GenreModel.name.in_(genres)
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



@router.get("/", response_model=MovieListResponseSchema)
async def get_movies(
    filters: MovieFilterSchema = Depends(),
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=20)] = 10,
    db: AsyncSession = Depends(get_db),
):
    query = select(MovieModel)

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


@router.post(
    "/", response_model=MovieDetailSchema, status_code=status.HTTP_201_CREATED
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

@router.get("/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await check_exists_movie(db=db, movie_id=movie_id)

    await db.refresh(movie, ["genres", "stars", "directors", "certification"])

    return movie

@router.delete("/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    await check_exists_movie(db=db, movie_id=movie_id)
    await db.execute(delete(MovieModel).where(MovieModel.id == movie_id))
    await db.commit()

@router.patch("/{movie_id}/")
async def update_movie(
    movie_id: int, movie: MovieUpdateSchema, db: AsyncSession = Depends(get_db)
):

    db_movie = await check_exists_movie(db=db, movie_id=movie_id)


    update_data = movie.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field not in ("genres", "stars", "directors", "certification"):
            setattr(db_movie, field, value)

    await db.commit()
    await db.refresh(
        db_movie, attribute_names=["genres", "stars", "directors", "certification"]
    )

    return {"detail": "Movie updated successfully."}

@router.post(
    "/{movie_id}/add_reaction/", response_model=MessageResponseSchema
)
async def add_reaction(
        movie_id: int,
        data: ReactionRequestSchema,
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    reactions = {
        1: "Liked",
        -1: "Disliked",
    }
    await check_exists_movie(db=db, movie_id=movie_id)

    if data.value == 0:
        await db.execute(delete(MovieReactionModel).where(
         MovieReactionModel.movie_id == movie_id,
            MovieReactionModel.user_id == user.id
            )
        )
        await db.commit()
        return {"message": "You have successfully removed the reaction."}

    db_reaction = await db.scalar(select(MovieReactionModel).where(
        MovieReactionModel.movie_id == movie_id,
        MovieReactionModel.user_id == user.id
        )
    )

    if not db_reaction:
        new_reaction = MovieReactionModel(
            movie_id=movie_id,
            user_id=user.id,
            value=data.value
        )
        db.add(new_reaction)
        await db.commit()

        return {"message": f"You {reactions[data.value]} this movie."}

    db_reaction.value = data.value
    db.add(db_reaction)
    await db.commit()
    return {"message": f"You {reactions[data.value]} this movie."}


@router.post("/{movie_id}/add_comment/", response_model=CommentResponseSchema)
async def add_comment(
        movie_id: int,
        data: CommentRequestSchema,
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    await check_exists_movie(db=db, movie_id=movie_id)

    db_comment = MovieCommentModel(
        text=data.text,
        user_id=user.id,
        movie_id=movie_id,
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)

    return db_comment


@router.post("/{movie_id}/add_comment/reply/", response_model=CommentReplyResponseSchema)
async def reply_comment(
        movie_id: int,
        data: CommentReplyRequestSchema,
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    await check_exists_movie(db=db, movie_id=movie_id)

    db_comment = await db.scalar(select(MovieCommentModel).where(MovieCommentModel.id == data.parent_id))

    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment does not exist."
        )

    new_comment = MovieCommentModel(
        text=data.text,
        user_id=user.id,
        movie_id=movie_id,
        parent_id=data.parent_id
    )
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)

    return new_comment
