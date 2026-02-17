import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from auxiliary_functions.movies import (
    build_url,
    check_exists_movie,
    filtering_movie,
    sorting_movie,
)

from auxiliary_functions.movies import get_current_user
from database import UserModel, MovieReactionModel
from database import get_db
from database.models.movies import (
    MovieModel,
    GenreModel,
    StarModel,
    DirectorModel,
    CertificationModel,
    MovieCommentModel,
    MovieRatingModel,
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
    MovieFilterSchema,
    RatingRequestSchema,
)
from security.permissions import check_moder_or_admin

router = APIRouter()


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    summary="Get a paginated list of movies",
    description=(
        "<h3>This endpoint retrieves a paginated list of movies from the database. "
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
                "application/json": {"example": {"detail": "No movies found."}}
            },
        }
    },
)
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
    "/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new movie",
    description=(
        "<h3>This endpoint allows clients to add a new movie to the database. "
        "It accepts details such as name, date, genres, stars, and "
        "other attributes.</h3>"
    ),
    responses={
        409: {
            "description": "Movie already exists with same parameters.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A movie with the name '{db_movie.name}', time '{db_movie.time}' and release year '{db_movie.year}' already exists."
                    }
                }
            },
        },
        500: {
            "description": "An error occurred while creating movie.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while creating movie."}
                }
            },
        },
    },
)
async def create_movie(
    movie: MovieCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(check_moder_or_admin),
):
    db_movie = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == movie.name,
            MovieModel.time == movie.time,
            MovieModel.year == movie.year,
        )
    )
    if db_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{db_movie.name}', time '{db_movie.time}' and release year '{db_movie.year}' already exists.",
        )

    try:
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
            select(CertificationModel).where(
                CertificationModel.name == movie.certification
            )
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

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating movie.",
        )


@router.get(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Get movie details by ID",
    description=(
        "<h3>Fetch detailed information about a specific movie by its unique ID. "
        "This endpoint retrieves all available details for the movie. If the movie with the given "
        "ID is not found, a 404 error will be returned.</h3>"
    ),
    responses={
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
    },
)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await check_exists_movie(db=db, movie_id=movie_id)

    await db.refresh(movie, ["genres", "stars", "directors", "certification"])

    return movie


@router.delete(
    "/{movie_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a movie by ID",
    description=(
        "<h3>Delete a specific movie from the database by its unique ID.</h3>"
        "<p>If the movie exists, it will be deleted. If it does not exist, "
        "a 404 error will be returned.</p>"
    ),
    responses={
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
        500: {
            "description": "An error occurred while deleting movie.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while deleting movie."}
                }
            },
        },
    },
)
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(check_moder_or_admin),
):
    await check_exists_movie(db=db, movie_id=movie_id)
    try:
        await db.execute(delete(MovieModel).where(MovieModel.id == movie_id))
        await db.commit()

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting movie.",
        )


@router.patch(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Update a movie by ID",
    description=(
        "<h3>Update details of a specific movie by its unique ID.</h3>"
        "<p>This endpoint updates the details of an existing movie. If the movie with "
        "the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
        500: {
            "description": "An error occurred while updating movie.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while updating movie."}
                }
            },
        },
    },
)
async def update_movie(
    movie_id: int,
    movie: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(check_moder_or_admin),
):

    db_movie = await check_exists_movie(db=db, movie_id=movie_id)

    update_data = movie.model_dump(exclude_unset=True)

    try:
        for field, value in update_data.items():
            if field not in ("genres", "stars", "directors", "certification"):
                setattr(db_movie, field, value)

        await db.commit()
        await db.refresh(
            db_movie, attribute_names=["genres", "stars", "directors", "certification"]
        )

        return db_movie

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating movie.",
        )


@router.post(
    "/{movie_id}/add_reaction/",
    response_model=MessageResponseSchema,
    summary="Add reaction to the movie",
    description=(
        "<h3>Add or remove reaction to the movie.</h3>"
        "<p>Expected value 0 - remove reaction, 1 - like, -1 - dislike. If the movie with "
        "the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
        500: {
            "description": "An error occurred while adding reaction.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while adding reaction."}
                }
            },
        },
    },
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

    try:
        if data.value == 0:
            await db.execute(
                delete(MovieReactionModel).where(
                    MovieReactionModel.movie_id == movie_id,
                    MovieReactionModel.user_id == user.id,
                )
            )
            await db.commit()
            return {"message": "You have successfully removed the reaction."}

        db_reaction = await db.scalar(
            select(MovieReactionModel).where(
                MovieReactionModel.movie_id == movie_id,
                MovieReactionModel.user_id == user.id,
            )
        )

        if not db_reaction:
            new_reaction = MovieReactionModel(
                movie_id=movie_id, user_id=user.id, value=data.value
            )
            db.add(new_reaction)
            await db.commit()

            return {"message": f"You {reactions[data.value]} this movie."}

        db_reaction.value = data.value
        await db.commit()
        return {"message": f"You {reactions[data.value]} this movie."}

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding reaction.",
        )


@router.post(
    "/{movie_id}/add_comment/",
    response_model=CommentResponseSchema,
    summary="Add comment to the movie",
    description=(
        "<h3>Add comment to the movie.</h3>"
        "<p>Endpoint apply to add comment for the movie. If the movie with "
        "the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
        500: {
            "description": "An error occurred while adding comment.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while adding comment."}
                }
            },
        },
    },
)
async def add_comment(
    movie_id: int,
    data: CommentRequestSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_exists_movie(db=db, movie_id=movie_id)

    try:
        db_comment = MovieCommentModel(
            text=data.text,
            user_id=user.id,
            movie_id=movie_id,
        )
        db.add(db_comment)
        await db.commit()
        await db.refresh(db_comment)

        return db_comment

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding comment.",
        )


@router.post(
    "/{movie_id}/add_comment/reply/",
    response_model=CommentReplyResponseSchema,
    summary="Reply to the comment under the movie",
    description=(
        "<h3>Reply to the comment under the movie.</h3>"
        "<p>Endpoint apply to reply to the comment under the movie by given ID. If the movie with "
        "the given ID does not exist, a 404 error is returned. If the comment with "
        "the given ID does not exist, a 400 error is returned</p>"
    ),
    responses={
        400: {
            "description": "Comment does not exist.",
            "content": {
                "application/json": {"example": {"detail": "Comment does not exist."}}
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
        500: {
            "description": "An error occurred while adding comment.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while adding comment."}
                }
            },
        },
    },
)
async def reply_comment(
    movie_id: int,
    data: CommentReplyRequestSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_exists_movie(db=db, movie_id=movie_id)

    db_comment = await db.scalar(
        select(MovieCommentModel).where(MovieCommentModel.id == data.parent_id)
    )

    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Comment does not exist."
        )
    try:
        new_comment = MovieCommentModel(
            text=data.text, user_id=user.id, movie_id=movie_id, parent_id=data.parent_id
        )
        db.add(new_comment)
        await db.commit()
        await db.refresh(new_comment)

        return new_comment

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding comment.",
        )


@router.post(
    "/{movie_id}/add_rating/",
    response_model=MessageResponseSchema,
    summary="Add rating to the movie",
    description=(
        "<h3>Add or remove rating to the movie.</h3>"
        "<p>Expected value in range 0 - 10 (int), 0 - remove rating, others is grade of movie. If the movie with "
        "the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
        500: {
            "description": "An error occurred while adding rating.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while adding rating."}
                }
            },
        },
    },
)
async def add_rating(
    movie_id: int,
    data: RatingRequestSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_exists_movie(db=db, movie_id=movie_id)

    try:
        if data.value == 0:
            await db.execute(
                delete(MovieRatingModel).where(
                    MovieRatingModel.movie_id == movie_id,
                    MovieRatingModel.user_id == user.id,
                )
            )
            await db.commit()
            return {"message": "You have successfully removed the movie rating."}

        db_rating = await db.scalar(
            select(MovieRatingModel).where(
                MovieRatingModel.movie_id == movie_id,
                MovieRatingModel.user_id == user.id,
            )
        )

        if not db_rating:
            new_rating = MovieRatingModel(
                movie_id=movie_id, user_id=user.id, value=data.value
            )
            db.add(new_rating)
            await db.commit()

            return {"message": f"You gave this movie a {data.value} rating."}

        db_rating.value = data.value
        await db.commit()
        return {"message": f"You gave this movie a {data.value} rating."}

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding rating.",
        )
