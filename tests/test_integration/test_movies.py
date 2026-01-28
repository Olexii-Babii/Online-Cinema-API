import math
from unittest.mock import patch

import pytest
from sqlalchemy import select, or_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from auxiliary_functions.movies import build_url
from database import MovieReactionModel, UserModel
from database.models.movies import MovieRatingModel, MovieCommentModel, MovieModel, StarModel, DirectorModel, GenreModel
from schemas.movies import MovieListItemSchema, MovieFilterSchema, MovieDetailSchema, GenresResponseSchema, \
    DirectorsResponseSchema, StarsResponseSchema, CertificationResponseSchema


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_get_movies_without_params(
        client, db_session, reset_db, create_test_user
):
    page = 1
    per_page = 10

    response = await client.get("/movies/")

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    movies = await db_session.scalars((select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    ))
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / per_page)

    result = {
        "movies": movies,
        "prev_page": (
            None
            if page == 1
            else build_url(filters=MovieFilterSchema(), per_page=per_page, page=page - 1)
        ),
        "next_page": (
            None
            if page >= total_pages
            else build_url(filters=MovieFilterSchema(), per_page=per_page, page=page + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_movies_with_search_param(
        client, db_session, reset_db, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "search": "tion"
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    search_term = f"%{filters['search']}%"
    movies = await db_session.scalars(query.where(
        or_(
            MovieModel.name.ilike(search_term),
            MovieModel.description.ilike(search_term),
            MovieModel.stars.any(StarModel.name.ilike(search_term)),
            MovieModel.directors.any(DirectorModel.name.ilike(search_term))
        )
    ))
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_movies_with_genres_params(
        client, db_session, reset_db, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "genres": "1,4"
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    genres = [int(genre.strip()) for genre in filters["genres"].split(",")]
    query = (query.join(MovieModel.genres).where(
        GenreModel.id.in_(genres))
    )
    movies = await db_session.scalars(query.distinct())
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_movies_with_year_param(
        client, db_session, reset_db, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "year": 2008
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    movies = await db_session.scalars(
        query.where(MovieModel.year == filters["year"])
    )
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_movies_with_year_from_year_to_params(
        client, db_session, reset_db, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "year_from": 2007,
        "year_to": 2020,
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    query = query.where(MovieModel.year >= filters["year_from"])
    query = query.where(MovieModel.year <= filters["year_to"])
    movies = await db_session.scalars(
        query
    )
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_movies_with_imdb_min_imdb_max_params(
        client, db_session, reset_db, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "imdb_min": 8.5,
        "imdb_max": 9.2,
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    query = query.where(MovieModel.imdb >= filters["imdb_min"])
    query = query.where(MovieModel.imdb <= filters["imdb_max"])
    movies = await db_session.scalars(
        query
    )
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_movies_with_directors_params(
        client, db_session, reset_db, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "directors": "1,4"
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    directors = [int(director.strip()) for director in filters["directors"].split(",")]
    query = query.join(MovieModel.directors).where(
        DirectorModel.id.in_(directors)
    )
    query = query.distinct()
    movies = await db_session.scalars(query)
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_movies_with_stars_params(
        client, db_session, reset_db, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "stars": "6,7"
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    stars = [int(star.strip()) for star in filters["stars"].split(",")]
    query = query.join(MovieModel.directors).where(
        StarModel.id.in_(stars)
    )
    query = query.distinct()
    movies = await db_session.scalars(query)
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_movies_with_price_min_price_max_params(
        client, db_session, reset_db, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "price_min": 14,
        "price_max": 18,
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    query = query.where(MovieModel.price >= filters["price_min"])
    query = query.where(MovieModel.price <= filters["price_max"])
    movies = await db_session.scalars(
        query
    )
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"



@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize("sort_field, model_field", [
    ("id", MovieModel.id.desc()),
    ("name", MovieModel.name.desc()),
    ("year", MovieModel.year.desc()),
    ("imdb", MovieModel.imdb.desc()),
    ("price", MovieModel.price.desc()),
])
async def test_get_movies_sort_by(
        client, db_session, reset_db, create_test_user, sort_field, model_field
):
    filters = {
        "page": 1,
        "per_page": 10,
        "sort_by": sort_field
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(model_field)
                    )

    movies = await db_session.scalars(
        query
    )
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize("order, order_setting", [
    ("asc", MovieModel.id.asc()),
    ("desc", MovieModel.id.desc()),
])
async def test_get_movies_order(
        client, db_session, reset_db, create_test_user, order, order_setting
):
    filters = {
        "page": 1,
        "per_page": 10,
        "order": order
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(order_setting)
                    )

    movies = await db_session.scalars(
        query
    )
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_movies_with_different_params(
        client, db_session, reset_db, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "genres": "1,4,5",
        "year_from": 2009,
        "imdb_min": 8.5
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    genres = [int(genre.strip()) for genre in filters["genres"].split(",")]
    query = query.join(MovieModel.genres).where(
        GenreModel.id.in_(genres))

    query = query.where(MovieModel.year >= filters["year_from"])
    query = query.where(MovieModel.imdb >= filters["imdb_min"])
    query = query.distinct()
    movies = await db_session.scalars(query)
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    count = len(movies)
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(search=filters["search"]),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize("page, per_page", [
    (1, 1),
    (2, 1),
    (3, 1),
    (1, 2),
    (2, 2),
])
async def test_get_movies_pagination(
        client, db_session, reset_db, create_test_user, page, per_page
):
    filters = {
        "page": page,
        "per_page": per_page,
    }

    response = await client.get("/movies/", params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .order_by(MovieModel.id.desc())
                    )
    count_query = select(func.count()).select_from(query.subquery())
    count = await db_session.scalar(count_query)

    query = query.offset((page - 1) * per_page).limit(per_page)
    movies = await db_session.scalars(
        query
    )
    movies = movies.all()

    movies = [MovieListItemSchema.model_validate(m).model_dump() for m in movies]
    total_pages = math.ceil(count / filters["per_page"])

    result = {
        "movies": movies,
        "prev_page": (
            None
            if filters["page"] == 1
            else build_url(
                filters=MovieFilterSchema(),
                per_page=filters["per_page"],
                page=filters["page"] - 1)
        ),
        "next_page": (
            None
            if filters["page"] >= total_pages
            else build_url(
                filters=MovieFilterSchema(),
                per_page=filters["per_page"],
                page=filters["page"] + 1)
        ),
        "total_pages": total_pages,
        "total_items": count,
    }
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_get_movie(
        client, db_session, reset_db, create_test_user
):
    response = await client.get("/movies/1/")
    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    movie_db = await db_session.scalar(select(MovieModel)
    .where(MovieModel.id == 1)
    .options(
            joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
            joinedload(MovieModel.directors)
        ))
    response_data = response.json()
    result = {
        "id": movie_db.id,
        "year": movie_db.year,
        "time": movie_db.time,
        "imdb": movie_db.imdb,
        "votes": movie_db.votes,
        "meta_score": movie_db.meta_score,
        "gross": movie_db.gross,
        "description": movie_db.description,
        "price": str(movie_db.price),
        "certification": CertificationResponseSchema.model_validate(movie_db.certification).model_dump(),
        "genres": [GenresResponseSchema.model_validate(g).model_dump() for g in movie_db.genres],
        "directors": [DirectorsResponseSchema.model_validate(d).model_dump() for d in movie_db.directors],
        "stars": [StarsResponseSchema.model_validate(s).model_dump() for s in movie_db.stars],

    }
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_not_existing_movie(
        client, db_session, reset_db, create_test_user
):
    response = await client.get("/movies/1000/")

    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "Movie with the given ID was not found.", "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_delete_movie(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.delete("/movies/1/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 403, "Expected status code does not match. Should be 403"
    response_data = response.json()
    assert response_data["detail"] == "You don't have permission to perform this action", \
        "Response data does not match"
    movie_db = await db_session.scalar(select(MovieModel).where(MovieModel.id == 1))
    assert movie_db is not None, "Movie should not to be deleted"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_delete_movie(
        client, db_session, reset_db, create_test_moder, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )

    response = await client.delete("/movies/1/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 204, "Expected status code does not match. Should be 204"
    assert response.text == "", "Response data does not match"
    movie_db = await db_session.scalar(select(MovieModel).where(MovieModel.id == 1))
    assert movie_db is None, "Movie should to be deleted"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_create_movie(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "name": "Test movie",
        "year": 2020,
        "time": 180,
        "imdb": 8.8,
        "votes": 10,
        "meta_score": 4,
        "gross": None,
        "description": "Test movie for tests",
        "price": None,
        "certification": "Test",
        "genres": ["Drama", "Test genre"],
        "stars": ["Test star", "Leonardo DiCaprio"],
        "directors": ["Leonardo DiCaprio", "Test director"]
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post("/movies/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    assert response.status_code == 403, "Expected status code does not match. Should be 403"
    response_data = response.json()
    assert response_data["detail"] == "You don't have permission to perform this action", \
        "Response data does not match"
    movie_db = await db_session.scalar(select(MovieModel).where(MovieModel.name == payload["name"]))
    assert movie_db is None, "Movie should not to be created"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_create_movie(
        client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {
        "name": "Test movie",
        "year": 2020,
        "time": 180,
        "imdb": 8.8,
        "votes": 10,
        "description": "Test movie for tests",
        "certification": "Test",
        "genres": ["Drama", "Test genre"],
        "stars": ["Test star", "Leonardo DiCaprio"],
        "directors": ["Christopher Nolan", "Test director"]
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )

    response = await client.post("/movies/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    assert response.status_code == 201, "Expected status code does not match. Should be 201"
    response_data = response.json()
    movie_db = await db_session.scalar(select(MovieModel)
        .options(joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
            joinedload(MovieModel.directors),
            joinedload(MovieModel.certification)
                 )
        .where(MovieModel.name == payload["name"]))
    result = {
        "id": movie_db.id,
        "year": payload["year"],
        "time": payload["time"],
        "imdb": payload["imdb"],
        "votes": payload["votes"],
        "meta_score": None,
        "gross": None,
        "description": payload["description"],
        "price":  None,
        "certification": {"id": movie_db.certification.id, "name": movie_db.certification.name},
        "genres": [{"id": g.id, "name": g.name} for g in movie_db.genres],
        "directors": [{"id": d.id, "name": d.name} for d in movie_db.directors],
        "stars": [{"id": s.id, "name": s.name} for s in movie_db.stars],

    }
    assert movie_db is not None, "Movie should to be created"

    assert response_data == result, "Response data does not match"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_create_movie_twice(
        client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {
        "name": "Test movie",
        "year": 2020,
        "time": 180,
        "imdb": 8.8,
        "votes": 10,
        "description": "Test movie for tests",
        "certification": "Test",
        "genres": ["Drama", "Test genre"],
        "stars": ["Test star", "Leonardo DiCaprio"],
        "directors": ["Christopher Nolan", "Test director"]
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )

    response = await client.post("/movies/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    assert response.status_code == 201, "Expected status code does not match. Should be 201"
    response_data = response.json()
    movie_db = await db_session.scalar(select(MovieModel)
        .options(joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
            joinedload(MovieModel.directors),
            joinedload(MovieModel.certification)
                 )
        .where(MovieModel.name == payload["name"]))
    result = {
        "id": movie_db.id,
        "year": payload["year"],
        "time": payload["time"],
        "imdb": payload["imdb"],
        "votes": payload["votes"],
        "meta_score": None,
        "gross": None,
        "description": payload["description"],
        "price":  None,
        "certification": {"id": movie_db.certification.id, "name": movie_db.certification.name},
        "genres": [{"id": g.id, "name": g.name} for g in movie_db.genres],
        "directors": [{"id": d.id, "name": d.name} for d in movie_db.directors],
        "stars": [{"id": s.id, "name": s.name} for s in movie_db.stars],

    }
    assert movie_db is not None, "Movie should to be created"

    assert response_data == result, "Response data does not match"

    second_response = await client.post("/movies/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    assert second_response.status_code == 409, "Expected status code does not match. Should be 409"
    movies_db = await db_session.scalars(select(MovieModel).where(
        MovieModel.name == payload["name"],
        MovieModel.year == payload["year"],
        MovieModel.time == payload["time"],
    ))
    result = movies_db.all()
    assert len(result) == 1, "Movie with same name, time and year should not to be created"
    second_response_data = second_response.json()
    assert second_response_data["detail"] == f"""A movie with the name '{payload["name"]}', time '{payload["time"]}' and release year '{payload["year"]}' already exists.""", "Response data does not match"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_create_movie_sqlalchemy_error(
        client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {
        "name": "Test movie",
        "year": 2020,
        "time": 180,
        "imdb": 8.8,
        "votes": 10,
        "description": "Test movie for tests",
        "certification": "Test",
        "genres": ["Drama", "Test genre"],
        "stars": ["Test star", "Leonardo DiCaprio"],
        "directors": ["Christopher Nolan", "Test director"]
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )

    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/movies/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

        assert response.status_code == 500, "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data["detail"] == "An error occurred while creating movie.", "Response data does not match"

        movie_db = await db_session.scalar(select(MovieModel)
            .where(MovieModel.name == payload["name"]))

        assert movie_db is None, "Movie should not to be created"



@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize("parameter", [
    ({"name": "a" * 260}),
    ({"year": 1899}),
    ({"imdb": -1}),
    ({"imdb": 11}),
    ({"time": -1}),
    ({"votes": -1}),
])
async def test_moder_create_movie_with_invalid_data(
        client, db_session, reset_db, create_test_moder, jwt_manager, parameter
):
    payload = {
        "name": parameter.get("name", "Test movie"),
        "year": parameter.get("year", 2020),
        "time": parameter.get("time", 180),
        "imdb": parameter.get("imdb", 8.8),
        "votes": parameter.get("votes", 10),
        "description": "Test movie for tests",
        "certification": "Test",
        "genres": ["Drama", "Test genre"],
        "stars": ["Test star", "Leonardo DiCaprio"],
        "directors": ["Christopher Nolan", "Test director"]
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )

    response = await client.post("/movies/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    assert response.status_code == 422, "Expected status code does not match. Should be 422"

    movie_db = await db_session.scalar(select(MovieModel)
        .where(MovieModel.name == payload["name"]))
    assert movie_db is None, "Movie should not to be created"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_update_movie(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "name": "Test movie",
        "year": 2020,
        "time": 180,
        "imdb": 8.8,
        "votes": 10,
        "meta_score": 4,
        "gross": None,
        "description": "Test movie for tests",
        "price": None,
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    movie = await db_session.scalar(select(MovieModel).where(MovieModel.id == 1))

    assert movie.name != payload["name"], "Movies names should be different."

    response = await client.patch("/movies/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    assert response.status_code == 403, "Expected status code does not match. Should be 403"
    response_data = response.json()
    assert response_data["detail"] == "You don't have permission to perform this action", \
        "Response data does not match"
    await db_session.refresh(movie)
    assert movie.name != payload["name"] , "Movie name should not be changed"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_update_movie_all_fields(
        client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {
        "name": "Test movie",
        "year": 2020,
        "time": 180,
        "imdb": 8.8,
        "votes": 10,
        "meta_score": 4.0,
        "gross": 8.0,
        "description": "Test movie for tests",
        "price": 12,
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )

    movie = await db_session.scalar(select(MovieModel)
        .where(MovieModel.id == 1))

    assert movie.name != payload["name"], "Movies names should be different."
    assert movie.description != payload["description"], "Movies names should be different."
    assert movie.price != payload["price"], "Movies names should be different."

    response = await client.patch("/movies/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    response_data = response.json()
    db_session.expire_all()

    movie_db = await db_session.scalar(select(MovieModel)
                                       .options(
        joinedload(MovieModel.stars),
        joinedload(MovieModel.genres),
        joinedload(MovieModel.directors),
        joinedload(MovieModel.certification)
    )
                                       .where(MovieModel.id == 1))

    assert movie_db.name == payload["name"], "Movie name should be changed"

    result = {
        "id": movie_db.id,
        "year": payload["year"],
        "time": payload["time"],
        "imdb": payload["imdb"],
        "votes": payload["votes"],
        "meta_score": payload["meta_score"],
        "gross": payload["gross"],
        "description": payload["description"],
        "price": str(payload["price"]),
        "certification": {"id": movie_db.certification.id, "name": movie_db.certification.name},
        "genres": [{"id": g.id, "name": g.name} for g in movie_db.genres],
        "directors": [{"id": d.id, "name": d.name} for d in movie_db.directors],
        "stars": [{"id": s.id, "name": s.name} for s in movie_db.stars],

    }
    assert response_data == result, "Response data does not match"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_update_not_existing_movie(
        client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {
        "name": "Test movie",
        "year": 2020,
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )

    response = await client.patch("/movies/1000/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "Movie with the given ID was not found.", "Response data does not match"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_update_movie_sqlalchemy_error(
        client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {
        "name": "Test movie",
        "year": 2020,
        "time": 180,
        "imdb": 8.8,
        "votes": 10,
        "meta_score": 4.0,
        "gross": 8.0,
        "description": "Test movie for tests",
        "price": 12
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )
    movie_db = await db_session.scalar(select(MovieModel).where(MovieModel.id == 1))

    assert movie_db.name != payload["name"], "Movies names should be different."

    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.patch("/movies/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

        assert response.status_code == 500, "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data["detail"] == "An error occurred while updating movie.", "Response data does not match"

        await db_session.refresh(movie_db)

        assert movie_db.name != payload["name"], "Movies names should not be changed."


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize("parameter", [
    ({"name": "a" * 260}),
    ({"year": 1899}),
    ({"imdb": -1}),
    ({"imdb": 11}),
    ({"price": -1}),
    ({"time": -1}),
    ({"votes": -1}),
])
async def test_moder_update_movie_with_invalid_data(
        client, db_session, reset_db, create_test_moder, jwt_manager, parameter
):
    payload = {
        "name": parameter.get("name", "Test movie"),
        "year": parameter.get("year", 2020),
        "time": parameter.get("time", 180),
        "imdb": parameter.get("imdb", 8.8),
        "votes": parameter.get("votes", 10),
        "description": "Test movie for tests",
        "price": parameter.get("price", 13),
        "certification": "Test",
        "genres": ["Drama", "Test genre"],
        "stars": ["Test star", "Leonardo DiCaprio"],
        "directors": ["Christopher Nolan", "Test director"]
    }
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )

    response = await client.patch("/movies/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    assert response.status_code == 422, "Expected status code does not match. Should be 422"

    movie_db = await db_session.scalar(select(MovieModel)
        .where(MovieModel.id == 1)
    )
    for field, invalid_value in parameter.items():
        db_value = getattr(movie_db, field)
        assert db_value != invalid_value, "Movie should not to be changed"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_delete_not_existing_movie(
        client, db_session, reset_db, create_test_moder, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_moder.email,
            "user_id": create_test_moder.id
        }
    )

    response = await client.delete("/movies/1000/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "Movie with the given ID was not found.", "Response data does not match"



@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize("reaction_value, reaction", [
    (1, "Liked"),
    (-1, "Disliked")
])
async def test_add_reaction_to_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user, reaction_value, reaction
):
    payload = {
        "value": reaction_value
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    reaction_db = await db_session.scalar(select(MovieReactionModel).where(
        MovieReactionModel.movie_id == 1,
        MovieReactionModel.user_id == create_test_user.id
    ))

    assert reaction_db is None, "New user has no reaction."

    response = await client.post(
        "/movies/1/add_reaction/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    response_data = response.json()
    assert response_data["message"] == f"You {reaction} this movie.", "Response data does not match."

    new_reaction_db = await db_session.scalar(select(MovieReactionModel).where(
        MovieReactionModel.movie_id == 1,
        MovieReactionModel.user_id == create_test_user.id
    ))

    assert new_reaction_db is not None, "Reaction should be created after request"
    assert new_reaction_db.value == payload["value"], "Reaction value should be equal to payload."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_add_reaction_to_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 1
    }

    response = await client.post("/movies/1/add_reaction/", json=payload)

    assert response.status_code == 401, "Expected status code does not match. Should be 401"

    response_data = response.json()

    assert response_data["detail"] == "Authorization header is missing", "Response data does not match."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_reaction_to_the_not_existing_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 1
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1000/add_reaction/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 404, "Expected status code does not match. Should be 404"

    response_data = response.json()

    assert response_data["detail"] == "Movie with the given ID was not found.", "Response data does not match."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_not_existing_reaction_from_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 0
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1/add_reaction/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    response_data = response.json()

    assert response_data["message"] == "You have successfully removed the reaction.", "Response data does not match."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_reaction_from_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):

    payload = {
        "value": 1
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    reaction_db = await db_session.scalar(select(MovieReactionModel).where(
        MovieReactionModel.movie_id == 1,
        MovieReactionModel.user_id == create_test_user.id
    ))

    assert reaction_db is None, "New user has no reaction"

    response = await client.post(
        "/movies/1/add_reaction/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    response_data = response.json()
    assert response_data["message"] == f"You Liked this movie.", "Response data does not match."

    new_reaction_db = await db_session.scalar(select(MovieReactionModel).where(
        MovieReactionModel.movie_id == 1,
        MovieReactionModel.user_id == create_test_user.id
    ))

    assert new_reaction_db is not None, "Reaction should be created after request"
    assert new_reaction_db.value == payload["value"], "Reaction value should be equal to payload"

    delete_payload = {
        "value": 0
    }

    delete_response = await client.post(
        "/movies/1/add_reaction/", json=delete_payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert delete_response.status_code == 200, "Expected status code does not match. Should be 200"

    delete_response_data = delete_response.json()

    assert delete_response_data["message"] == "You have successfully removed the reaction.", \
        "Response data does not match."

    delete_reaction_db = await db_session.scalar(select(MovieReactionModel).where(
        MovieReactionModel.movie_id == 1,
        MovieReactionModel.user_id == create_test_user.id
    ))

    assert delete_reaction_db is None, "Reaction should be removed."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_reaction_to_the_movie_with_existing_reaction(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 1
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    reaction= await db_session.scalar(select(MovieReactionModel).where(
        MovieReactionModel.movie_id == 1,
        MovieReactionModel.user_id == create_test_user.id
    ))

    assert reaction is None, "New user has no reaction."

    response = await client.post(
        "/movies/1/add_reaction/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    response_data = response.json()
    assert response_data["message"] == f"You Liked this movie.", "Response data does not match."

    reaction_db = await db_session.scalar(select(MovieReactionModel).where(
        MovieReactionModel.movie_id == 1,
        MovieReactionModel.user_id == create_test_user.id
    ))

    assert reaction_db is not None, "Reaction should be created after request"
    assert reaction_db.value == payload["value"], "Reaction value should be equal to payload."

    new_payload = {
        "value": -1
    }

    new_response = await client.post(
        "/movies/1/add_reaction/", headers={"Authorization": f"Bearer {access_token}"}, json=new_payload
    )

    assert new_response.status_code == 200, "Expected status code does not match. Should be 200"

    new_response_data = new_response.json()
    assert new_response_data["message"] == f"You Disliked this movie.", "Response data does not match."

    new_reaction_db = await db_session.scalar(select(MovieReactionModel).where(
        MovieReactionModel.movie_id == 1,
        MovieReactionModel.user_id == create_test_user.id
    ))
    await db_session.refresh(new_reaction_db)

    assert new_reaction_db is not None, "Reaction should be exist after request"
    assert new_reaction_db.value == new_payload["value"], "Reaction value should be equal to payload."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_reaction_to_the_movie_sqlalchemy_error(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 1
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):

        response = await client.post(
            "/movies/1/add_reaction/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
        )

        assert response.status_code == 500, "Expected status code does not match. Should be 500"

        response_data = response.json()
        assert response_data["detail"] == "An error occurred while adding reaction.", "Response data does not match."

        reaction_db = await db_session.scalar(select(MovieReactionModel).where(
            MovieReactionModel.movie_id == 1,
            MovieReactionModel.user_id == create_test_user.id
        ))

        assert reaction_db is None, "Reaction should not be created."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_reaction_to_the_movie_with_invalid_value(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 7
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1/add_reaction/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 422, "Expected status code does not match. Should be 422"




@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_rating_to_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 5
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    rating_db = await db_session.scalar(select(MovieRatingModel).where(
        MovieRatingModel.movie_id == 1,
        MovieRatingModel.user_id == create_test_user.id
    ))

    assert rating_db is None, "New user has no rating movie."

    response = await client.post(
        "/movies/1/add_rating/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    response_data = response.json()
    assert response_data["message"] == f"You gave this movie a {payload["value"]} rating.", \
        "Response data does not match."

    new_rating_db = await db_session.scalar(select(MovieRatingModel).where(
        MovieRatingModel.movie_id == 1,
        MovieRatingModel.user_id == create_test_user.id
    ))

    assert new_rating_db is not None, "Rating should be created after request"
    assert new_rating_db.value == payload["value"], "Rating value should be equal to payload."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_add_rating_to_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 3
    }

    response = await client.post("/movies/1/add_rating/", json=payload)

    assert response.status_code == 401, "Expected status code does not match. Should be 401"

    response_data = response.json()

    assert response_data["detail"] == "Authorization header is missing", "Response data does not match."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_rating_to_the_not_existing_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 6
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1000/add_rating/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 404, "Expected status code does not match. Should be 404"

    response_data = response.json()

    assert response_data["detail"] == "Movie with the given ID was not found.", "Response data does not match."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_not_existing_rating_from_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 0
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1/add_rating/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    response_data = response.json()

    assert response_data["message"] == "You have successfully removed the movie rating.", "Response data does not match."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_rating_from_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):

    payload = {
        "value": 7
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    rating_db = await db_session.scalar(select(MovieRatingModel).where(
        MovieRatingModel.movie_id == 1,
        MovieRatingModel.user_id == create_test_user.id
    ))

    assert rating_db is None, "New user has no rating movie"

    response = await client.post(
        "/movies/1/add_rating/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    response_data = response.json()
    assert response_data["message"] == f"You gave this movie a {payload["value"]} rating.", "Response data does not match."

    new_rating_db = await db_session.scalar(select(MovieRatingModel).where(
        MovieRatingModel.movie_id == 1,
        MovieRatingModel.user_id == create_test_user.id
    ))

    assert new_rating_db is not None, "Rating should be created after request"
    assert new_rating_db.value == payload["value"], "Rating value should be equal to payload"

    delete_payload = {
        "value": 0
    }

    delete_response = await client.post(
        "/movies/1/add_rating/", json=delete_payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert delete_response.status_code == 200, "Expected status code does not match. Should be 200"

    delete_response_data = delete_response.json()

    assert delete_response_data["message"] == "You have successfully removed the movie rating.", \
        "Response data does not match."

    delete_rating_db = await db_session.scalar(select(MovieRatingModel).where(
        MovieRatingModel.movie_id == 1,
        MovieRatingModel.user_id == create_test_user.id
    ))

    assert delete_rating_db is None, "Rating should be removed."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_rating_to_the_movie_with_existing_rating(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 5
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    rating = await db_session.scalar(select(MovieRatingModel).where(
        MovieRatingModel.movie_id == 1,
        MovieRatingModel.user_id == create_test_user.id
    ))

    assert rating is None, "New user has no rating movie."

    response = await client.post(
        "/movies/1/add_rating/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    response_data = response.json()
    assert response_data["message"] == f"You gave this movie a {payload["value"]} rating.", \
        "Response data does not match."

    rating_db = await db_session.scalar(select(MovieRatingModel).where(
        MovieRatingModel.movie_id == 1,
        MovieRatingModel.user_id == create_test_user.id
    ))

    assert rating_db is not None, "Rating should be created after request"
    assert rating_db.value == payload["value"], "Rating value should be equal to payload."

    new_payload = {
        "value": 3
    }

    new_response = await client.post(
        "/movies/1/add_rating/", headers={"Authorization": f"Bearer {access_token}"}, json=new_payload
    )

    assert new_response.status_code == 200, "Expected status code does not match. Should be 200"

    new_response_data = new_response.json()
    assert new_response_data["message"] == f"You gave this movie a {new_payload["value"]} rating.", \
        "Response data does not match."

    new_rating_db = await db_session.scalar(select(MovieRatingModel).where(
        MovieRatingModel.movie_id == 1,
        MovieRatingModel.user_id == create_test_user.id
    ))
    await db_session.refresh(new_rating_db)

    assert new_rating_db is not None, "Rating should be exist after request"
    assert new_rating_db.value == new_payload["value"], "Rating value should be equal to payload."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_rating_to_the_movie_sqlalchemy_error(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 7
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):

        response = await client.post(
            "/movies/1/add_rating/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
        )

        assert response.status_code == 500, "Expected status code does not match. Should be 500"

        response_data = response.json()
        assert response_data["detail"] == "An error occurred while adding rating.", "Response data does not match."

        rating_db = await db_session.scalar(select(MovieRatingModel).where(
            MovieRatingModel.movie_id == 1,
            MovieRatingModel.user_id == create_test_user.id
        ))

        assert rating_db is None, "Rating should not be created."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_rating_to_the_movie_with_invalid_value(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 11
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1/add_rating/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 422, "Expected status code does not match. Should be 422"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_comment_to_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "text": "I love this movie."
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1/add_comment/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    comment_db = await db_session.scalar(select(MovieCommentModel).where(
        MovieCommentModel.movie_id == 1,
        MovieCommentModel.user_id == create_test_user.id)
    )
    assert comment_db is not None, "Comment should be exist after request"
    response_data = response.json()
    result = {
        "id": comment_db.id,
        "text": comment_db.text,
        "user_id": comment_db.user_id,
        "movie_id": comment_db.movie_id,
        "created_at": comment_db.created_at.isoformat()
    }
    assert response_data == result, \
    "Response data does not match."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_add_comment_to_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "text": "I love this movie."
    }

    response = await client.post(
        "/movies/1/add_comment/", json=payload
    )

    assert response.status_code == 401, "Expected status code does not match. Should be 401"
    response_data = response.json()
    assert response_data["detail"] == "Authorization header is missing", "Response data does not match."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_comment_to_not_existing_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "text": "I love this movie."
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1000/add_comment/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()

    assert response_data["detail"] == "Movie with the given ID was not found.", "Response data does not match."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_comment_to_the_movie_sqlalchemy_error(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "text": "I love this movie."
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post(
            "/movies/1/add_comment/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 500, "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data["detail"] == "An error occurred while adding comment.", "Response data does not match."

        comment_db = await db_session.scalar(select(MovieCommentModel).where(
          MovieCommentModel.movie_id == 1,
            MovieCommentModel.user_id == create_test_user.id)
        )
        assert comment_db is None, "Comment should not be exist."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_comment_to_the_movie_with_invalid_data(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 1
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1/add_comment/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 422, "Expected status code does not match. Should be 422"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_reply_comment_to_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "text": "I love this movie.",
        "parent_id": 1
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.post(
        "/movies/1/add_comment/reply/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    comment_db = await db_session.scalar(select(MovieCommentModel).where(
        MovieCommentModel.movie_id == 1,
        MovieCommentModel.user_id == db_user.id,
        MovieCommentModel.text == payload["text"],
    )
    )
    assert comment_db is not None, "Comment should be exist after request"
    response_data = response.json()
    result = {
        "id": comment_db.id,
        "text": comment_db.text,
        "user_id": comment_db.user_id,
        "movie_id": comment_db.movie_id,
        "created_at": comment_db.created_at.isoformat(),
        "parent_id": comment_db.parent_id,
    }
    assert response_data == result, \
    "Response data does not match."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_add_reply_comment_to_the_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "text": "I love this movie.",
        "parent_id": 1
    }

    response = await client.post(
        "/movies/1/add_comment/reply/", json=payload
    )

    assert response.status_code == 401, "Expected status code does not match. Should be 401"
    response_data = response.json()
    assert response_data["detail"] == "Authorization header is missing", "Response data does not match."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_reply_comment_to_not_existing_movie(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "text": "I love this movie.",
        "parent_id": 1
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.post(
        "/movies/1000/add_comment/reply/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()

    assert response_data["detail"] == "Movie with the given ID was not found.", "Response data does not match."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_reply_comment_to_not_existing_parent_comment(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "text": "I love this movie.",
        "parent_id": 100
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.post(
        "/movies/1/add_comment/reply/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 400, "Expected status code does not match. Should be 400"
    response_data = response.json()

    assert response_data["detail"] == "Comment does not exist.", "Response data does not match."



@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_reply_comment_to_the_movie_sqlalchemy_error(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "text": "I love this movie.",
        "parent_id": 1
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post(
            "/movies/1/add_comment/reply/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 500, "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data["detail"] == "An error occurred while adding comment.", "Response data does not match."

        comment_db = await db_session.scalar(select(MovieCommentModel).where(
          MovieCommentModel.movie_id == 1,
            MovieCommentModel.user_id == create_test_user.id,
            MovieCommentModel.text == payload["text"]
        )
        )
        assert comment_db is None, "Comment should not be exist."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_reply_comment_to_the_movie_with_invalid_data(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    payload = {
        "value": 1
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/movies/1/add_comment/reply/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 422, "Expected status code does not match. Should be 422"


