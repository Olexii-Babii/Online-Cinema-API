from unittest.mock import patch

import pytest
from sqlalchemy import select, func, or_
from sqlalchemy.exc import SQLAlchemyError

from database import GenreModel, MovieModel


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_all_genres(
    client, db_session, reset_db, create_test_user, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={"email": create_test_user.email, "user_id": create_test_user.id}
    )
    genres = await db_session.execute(
        select(GenreModel.name, func.count(MovieModel.id).label("movie_count"))
        .outerjoin(GenreModel.movies)
        .group_by(GenreModel.id)
    )
    genres = genres.mappings().all()

    response = await client.get(
        "/genres/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        response.status_code == 200
    ), "Expected status code does not match. Should be 200"
    response_data = response.json()
    assert response_data == genres, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_get_all_genres(client, db_session, reset_db):
    response = await client.get("/genres/")

    assert (
        response.status_code == 401
    ), "Expected status code does not match. Should be 401"
    response_data = response.json()
    assert response_data == {
        "detail": "Authorization header is missing"
    }, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_create_genre(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/genres/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_create_genre_twice(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/genres/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"

    new_response = await client.post(
        "/genres/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        new_response.status_code == 409
    ), "Expected status code does not match. Should be 409"
    new_response_data = new_response.json()
    assert new_response_data == {
        "detail": "Genre already exists."
    }, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_create_genre(
    client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {"name": "Test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_user.email, "user_id": create_test_user.id}
    )

    response = await client.post(
        "/genres/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 403
    ), "Expected status code does not match. Should be 403"
    response_data = response.json()
    assert response_data == {
        "detail": "You don't have permission to perform this action"
    }, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_genre_sqlalchemy_error(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    with patch("routes.genres.AsyncSession.commit", side_effect=SQLAlchemyError):

        response = await client.post(
            "/genres/",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert (
            response.status_code == 500
        ), "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data == {
            "detail": "An error occurred while creating the genre."
        }, "Expected message does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_update_genre(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/genres/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"

    genre = await db_session.scalar(
        select(GenreModel).where(GenreModel.name == payload["name"])
    )

    new_payload = {"name": "New test genre"}

    new_response = await client.patch(
        f"/genres/{genre.id}/",
        json=new_payload,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert (
        new_response.status_code == 200
    ), "Expected status code does not match. Should be 200"
    response_data = new_response.json()
    assert response_data["name"] == new_payload["name"], "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_update_not_existing_genre(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "New test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    new_response = await client.patch(
        f"/genres/1000/",
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert (
        new_response.status_code == 404
    ), "Expected status code does not match. Should be 404"
    response_data = new_response.json()
    assert (
        response_data["detail"] == "Genre with the given ID was not found."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_update_genre(
    client, db_session, reset_db, create_test_user, jwt_manager, create_test_moder
):
    payload = {"name": "Test genre"}

    moder_access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/genres/",
        headers={"Authorization": f"Bearer {moder_access_token}"},
        json=payload,
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"

    genre = await db_session.scalar(
        select(GenreModel).where(GenreModel.name == payload["name"])
    )

    new_payload = {"name": "New test genre"}

    user_access_token = jwt_manager.create_access_token(
        data={"email": create_test_user.email, "user_id": create_test_user.id}
    )

    response = await client.patch(
        f"/genres/{genre.id}/",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json=new_payload,
    )

    assert (
        response.status_code == 403
    ), "Expected status code does not match. Should be 403"
    response_data = response.json()
    assert response_data == {
        "detail": "You don't have permission to perform this action"
    }, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_update_genre_with_same_existing_name(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    genres = await db_session.scalars(
        select(GenreModel).where(or_(GenreModel.id == 1, GenreModel.id == 2))
    )
    genres = genres.all()

    payload = {"name": genres[1].name}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    new_response = await client.patch(
        f"/genres/{genres[0].id}/",
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert (
        new_response.status_code == 409
    ), "Expected status code does not match. Should be 409"
    response_data = new_response.json()
    assert (
        response_data["detail"]
        == f"Genre with this name ({payload["name"]}) already exists."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_genre_sqlalchemy_error(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    with patch("routes.genres.AsyncSession.commit", side_effect=SQLAlchemyError):

        response = await client.patch(
            "/genres/1/",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert (
            response.status_code == 500
        ), "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data == {
            "detail": "An error occurred while updating the genre."
        }, "Expected message does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_delete_genre(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/genres/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"

    genre = await db_session.scalar(
        select(GenreModel).where(GenreModel.name == payload["name"])
    )

    delete_response = await client.delete(
        f"/genres/{genre.id}/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        delete_response.status_code == 204
    ), "Expected status code does not match. Should be 204"

    deleted_genre = await db_session.scalar(
        select(GenreModel).where(GenreModel.name == payload["name"])
    )

    assert deleted_genre is None, "Genre was not deleted"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_delete_genre(
    client, db_session, reset_db, create_test_user, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={"email": create_test_user.email, "user_id": create_test_user.id}
    )

    response = await client.delete(
        "/genres/1/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        response.status_code == 403
    ), "Expected status code does not match. Should be 403"
    response_data = response.json()
    assert response_data == {
        "detail": "You don't have permission to perform this action"
    }, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_delete_genre_twice(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/genres/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"

    genre = await db_session.scalar(
        select(GenreModel).where(GenreModel.name == payload["name"])
    )

    first_response = await client.delete(
        f"/genres/{genre.id}/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        first_response.status_code == 204
    ), "Expected status code does not match. Should be 204"

    deleted_genre = await db_session.scalar(
        select(GenreModel).where(GenreModel.name == payload["name"])
    )

    assert deleted_genre is None, "Genre was not deleted"

    second_response = await client.delete(
        f"/genres/{genre.id}/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        second_response.status_code == 404
    ), "Expected status code does not match. Should be 404"

    second_response_data = second_response.json()
    assert (
        second_response_data["detail"] == "Genre with the given ID was not found."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_delete_not_existing_genre(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.delete(
        "/genres/100000/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        response.status_code == 404
    ), "Expected status code does not match. Should be 404"

    second_response_data = response.json()
    assert (
        second_response_data["detail"] == "Genre with the given ID was not found."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_delete_genre_with_movies(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.delete(
        "/genres/1/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        response.status_code == 409
    ), "Expected status code does not match. Should be 409"

    second_response_data = response.json()
    assert (
        second_response_data["detail"] == "There are already films with this genre."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_genre_sqlalchemy_error(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test genre"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    await client.post(
        "/genres/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    genre = await db_session.scalar(
        select(GenreModel).where(GenreModel.name == payload["name"])
    )

    with patch("routes.genres.AsyncSession.commit", side_effect=SQLAlchemyError):

        response = await client.delete(
            f"/genres/{genre.id}/", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert (
            response.status_code == 500
        ), "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data == {
            "detail": "An error occurred while deleting the genre."
        }, "Expected message does not match"
