import math
from unittest.mock import patch

import pytest
from sqlalchemy import select, func, or_
from sqlalchemy.exc import SQLAlchemyError

from auxiliary_functions.movies import build_url
from database import FavoriteModel, MovieModel, UserModel, StarModel, DirectorModel, GenreModel
from database.models.favorites import MoviesFavoritesModel
from schemas.movies import MovieFilterSchema, MovieListItemSchema, MovieSortField


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_get_favorite_movies(
        client, db_session, reset_db, jwt_manager
):
    response = await client.get("/favorites/")

    assert response.status_code == 401, "Expected status code does not match. Should be 401"
    response_data = response.json()
    assert response_data["detail"] == "Authorization header is missing", "Response data does not match"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_favorite_movies_without_params(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    page = 1
    per_page = 10
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    movies = await db_session.scalars((select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
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
async def test_get_favorite_movies_with_search_param(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "search": "tion"
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
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
async def test_get_favorite_movies_with_genres_params(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "genres": "1,4"
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
                        .order_by(MovieModel.id.desc())
                    )
    genres = [int(genre.strip()) for genre in filters["genres"].split(",")]
    movies = await db_session.scalars(query.join(MovieModel.genres).where(
        GenreModel.id.in_(genres))
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
async def test_get_favorite_movies_with_year_param(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "year": 2008
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
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
async def test_get_favorite_movies_with_year_from_year_to_params(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "year_from": 2007,
        "year_to": 2020,
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
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
async def test_get_favorite_movies_with_imdb_min_imdb_max_params(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "imdb_min": 8.5,
        "imdb_max": 9.2,
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
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
async def test_get_favorite_movies_with_directors_params(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "directors": "1,4"
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
                        .order_by(MovieModel.id.desc())
                    )
    directors = [int(director.strip()) for director in filters["directors"].split(",")]
    query = query.join(MovieModel.directors).where(
        DirectorModel.id.in_(directors)
    )
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
async def test_get_favorite_movies_with_stars_params(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "stars": "6,7"
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
                        .order_by(MovieModel.id.desc())
                    )
    stars = [int(star.strip()) for star in filters["stars"].split(",")]
    query = query.join(MovieModel.directors).where(
        StarModel.id.in_(stars)
    )
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
async def test_get_favorite_movies_with_price_min_price_max_params(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "price_min": 14,
        "price_max": 18,
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
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
async def test_get_favorite_movies_sort_by(
        client, db_session, reset_db, jwt_manager, create_test_user, sort_field, model_field
):
    filters = {
        "page": 1,
        "per_page": 10,
        "sort_by": sort_field
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
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
async def test_get_favorite_movies_order(
        client, db_session, reset_db, jwt_manager, create_test_user, order, order_setting
):
    filters = {
        "page": 1,
        "per_page": 10,
        "order": order
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
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
async def test_get_favorite_movies_with_different_params(
        client, db_session, reset_db, jwt_manager, create_test_user
):
    filters = {
        "page": 1,
        "per_page": 10,
        "genres": "1,4,5",
        "year_from": 2009,
        "imdb_min": 8.5
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
                        .order_by(MovieModel.id.desc())
                    )
    genres = [int(genre.strip()) for genre in filters["genres"].split(",")]
    query = query.join(MovieModel.genres).where(
        GenreModel.id.in_(genres))

    query = query.where(MovieModel.year >= filters["year_from"])
    query = query.where(MovieModel.imdb >= filters["imdb_min"])
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
async def test_get_favorite_movies_pagination(
        client, db_session, reset_db, jwt_manager, create_test_user, page, per_page
):
    filters = {
        "page": page,
        "per_page": per_page,
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"

    query = (select(MovieModel)
                        .join(MoviesFavoritesModel, MovieModel.id == MoviesFavoritesModel.c.movie_id)
                        .join(FavoriteModel, FavoriteModel.id == MoviesFavoritesModel.c.favorite_id)
                        .where(FavoriteModel.user_id == db_user.id)
                        .distinct()
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
async def test_user_get_movies_without_favorite_list(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "You don't have favorite movies.", "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_get_movies_favorite_without_movies(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )
    favorite = FavoriteModel(
        user_id=create_test_user.id,
    )
    db_session.add(favorite)
    await db_session.commit()

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "Your favorite movies list is empty.", "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_get_empty_movies_favorite_list(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    filters = {
        "page": 1,
        "per_page": 10,
        "search": "XMVKFME"
    }
    db_user = await db_session.scalar(select(UserModel).where(UserModel.id == 1))
    access_token = jwt_manager.create_access_token(
        data={
            "email": db_user.email,
            "user_id": db_user.id
        }
    )

    response = await client.get("/favorites/", headers={"Authorization": f"Bearer {access_token}"}, params=filters)

    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "No movies found.", "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_get_movies(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    response = await client.get("/favorites/")
    assert response.status_code == 401, "Expected status code does not match. Should be 401"
    response_data = response.json()
    assert response_data["detail"] == "Authorization header is missing", "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_movie_to_new_favorite_list(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "movie_id": 1,
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/favorites/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    result = {"movie_id": 1, "message": "You successfully added your favorite movie."}
    response_data = response.json()
    assert response_data == result, "Response data does not match"

    favorite = await db_session.scalar(select(FavoriteModel).where(FavoriteModel.user_id == create_test_user.id))
    favorite_movie = await db_session.scalar(select(func.count()).select_from(MoviesFavoritesModel).where(
        MoviesFavoritesModel.c.movie_id == 1,
        MoviesFavoritesModel.c.favorite_id == favorite.id,
    ))

    assert favorite_movie == 1, "Movie was not added to favorites."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_movie_to_favorite_twice(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "movie_id": 1,
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/favorites/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    result = {"movie_id": 1, "message": "You successfully added your favorite movie."}
    response_data = response.json()
    assert response_data == result, "Response data does not match"

    favorite = await db_session.scalar(select(FavoriteModel).where(FavoriteModel.user_id == create_test_user.id))
    favorite_movie = await db_session.scalar(select(func.count()).select_from(MoviesFavoritesModel).where(
        MoviesFavoritesModel.c.movie_id == 1,
        MoviesFavoritesModel.c.favorite_id == favorite.id,
    ))

    assert favorite_movie == 1, "Movie was not added to favorites."

    second_response = await client.post(
        "/favorites/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )
    assert second_response.status_code == 409, "Expected status code does not match. Should be 409"
    second_response_data = second_response.json()
    assert second_response_data["detail"] == "Movie already in favorites.", "Response data does not match"

    favorite = await db_session.scalar(select(FavoriteModel).where(FavoriteModel.user_id == create_test_user.id))
    favorite_movie = await db_session.scalar(select(func.count()).select_from(MoviesFavoritesModel).where(
        MoviesFavoritesModel.c.movie_id == 1,
        MoviesFavoritesModel.c.favorite_id == favorite.id,
    ))

    assert favorite_movie == 1, "Movie has not to be added to favorites twice."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_not_existing_movie_to_favorite(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "movie_id": 1000,
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/favorites/1000/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "Movie with the given ID was not found.", "Response data does not match"



@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_movie_to_existing_favorite_list(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "movie_id": 1,
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/favorites/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    result = {"movie_id": 1, "message": "You successfully added your favorite movie."}
    response_data = response.json()
    assert response_data == result, "Response data does not match"

    second_payload = {
        "movie_id": 2,
    }

    second_response = await client.post(
        "/favorites/2/", headers={"Authorization": f"Bearer {access_token}"}, json=second_payload
    )
    assert second_response.status_code == 200, "Expected status code does not match. Should be 200"
    second_result = {"movie_id": 2, "message": "You successfully added your favorite movie."}
    second_response_data = second_response.json()
    assert second_response_data == second_result, "Response data does not match"

    favorite = await db_session.scalar(select(FavoriteModel).where(FavoriteModel.user_id == create_test_user.id))
    favorite_movie = await db_session.scalar(select(func.count()).select_from(MoviesFavoritesModel).where(
        MoviesFavoritesModel.c.movie_id == 2,
        MoviesFavoritesModel.c.favorite_id == favorite.id,
    ))

    assert favorite_movie == 1, "Movie was not added to favorites."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_add_movie_to_favorite(
        client, db_session, reset_db, jwt_manager
):
    payload = {
        "movie_id": 1,
    }

    response = await client.post(
        "/favorites/1/", json=payload
    )

    assert response.status_code == 401, "Expected status code does not match. Should be 401"
    response_data = response.json()
    assert response_data["detail"] == "Authorization header is missing", "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_movie_to_favorite_sqlalchemy_error(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "movie_id": 1,
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    with patch("routes.favorites.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post(
            "/favorites/1/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
        )

        response.status_code = 500, "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data["detail"] == "An error occurred while adding the movie to favorites."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_movie_from_favorite(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "movie_id": 1,
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/favorites/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    result = {"movie_id": 1, "message": "You successfully added your favorite movie."}
    response_data = response.json()
    assert response_data == result, "Response data does not match"

    delete_response = await client.delete(
        "/favorites/1/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert delete_response.status_code == 204, "Expected status code does not match. Should be 204"
    assert delete_response.text == "", "Response data does not match"

    favorite = await db_session.scalar(select(FavoriteModel).where(FavoriteModel.user_id == create_test_user.id))
    favorite_movie = await db_session.scalar(select(func.count()).select_from(MoviesFavoritesModel).where(
        MoviesFavoritesModel.c.movie_id == 1,
        MoviesFavoritesModel.c.favorite_id == favorite.id,
    ))

    assert favorite_movie == 0, "Movie was not removed from favorites."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_not_existing_movie_from_favorite(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.delete(
        "/favorites/1000/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "Movie with the given ID was not found.", "Response data does not match."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_movie_from_not_existing_favorite(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.delete(
        "/favorites/1/", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 404, "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "You don't have favorite movies.", "Response data does not match."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_movie_not_favorite_movie_from_favorite_list(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "movie_id": 1,
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/favorites/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    result = {"movie_id": 1, "message": "You successfully added your favorite movie."}
    response_data = response.json()
    assert response_data == result, "Response data does not match"

    delete_response = await client.delete(
        "/favorites/2/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert delete_response.status_code == 409, "Expected status code does not match. Should be 409"
    delete_response_data = delete_response.json()
    assert delete_response_data["detail"] == "Movie is not in favorites.", "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_remove_movie_from_favorite_sqlalchemy_error(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {
        "movie_id": 1,
    }

    access_token = jwt_manager.create_access_token(
        data={
            "email": create_test_user.email,
            "user_id": create_test_user.id
        }
    )

    response = await client.post(
        "/favorites/1/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    result = {"movie_id": 1, "message": "You successfully added your favorite movie."}
    response_data = response.json()
    assert response_data == result, "Response data does not match"

    with (patch("routes.favorites.AsyncSession.commit", side_effect=SQLAlchemyError)):
        delete_response = await client.delete("/favorites/1/", headers={"Authorization": f"Bearer {access_token}"})
        assert delete_response.status_code == 500, "Expected status code does not match. Should be 500"
        delete_response_data = delete_response.json()
        assert delete_response_data["detail"] == "An error occurred while removing the movie from favorites.", \
        "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_remove_movie_from_favorite(
        client, db_session, reset_db, create_test_user, jwt_manager
):
    response = await client.delete("favorites/1/")

    assert response.status_code == 401, "Expected status code does not match. Should be 401"
    response_data = response.json()
    assert response_data["detail"] == "Authorization header is missing", "response data does not match"
