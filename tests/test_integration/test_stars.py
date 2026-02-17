from unittest.mock import patch

import pytest
from sqlalchemy import select, or_
from sqlalchemy.exc import SQLAlchemyError

from database import StarModel, UserModel, UserGroupModel, UserGroupEnum


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_empty_stars_list(
    client, db_session, reset_db, seed_user_groups, jwt_manager
):
    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )

    user = UserModel(
        email="testuser@example.com", password="Password12345@", group_id=user_group.id
    )
    user.is_active = True

    db_session.add(user)
    await db_session.commit()

    access_token = jwt_manager.create_access_token(
        data={"email": user.email, "user_id": user.id}
    )

    response = await client.get(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        response.status_code == 404
    ), "Expected status code does not match. Should be 404"
    response_data = response.json()
    assert response_data["detail"] == "No stars found.", "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_all_stars(
    client, db_session, reset_db, create_test_user, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={"email": create_test_user.email, "user_id": create_test_user.id}
    )
    stars = await db_session.scalars(select(StarModel))
    stars = stars.all()

    result = [{"id": star.id, "name": star.name} for star in stars]

    response = await client.get(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        response.status_code == 200
    ), "Expected status code does not match. Should be 200"
    response_data = response.json()
    assert response_data == result, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_user_get_all_stars(client, db_session, reset_db):
    response = await client.get("/stars/")

    assert (
        response.status_code == 401
    ), "Expected status code does not match. Should be 401"
    response_data = response.json()
    assert response_data == {
        "detail": "Authorization header is missing"
    }, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_create_star(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_create_star_twice(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"

    new_response = await client.post(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        new_response.status_code == 409
    ), "Expected status code does not match. Should be 409"
    new_response_data = new_response.json()
    assert new_response_data == {
        "detail": "Star already exists."
    }, "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_create_star(
    client, db_session, reset_db, create_test_user, jwt_manager
):
    payload = {"name": "Test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_user.email, "user_id": create_test_user.id}
    )

    response = await client.post(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
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
async def test_create_star_sqlalchemy_error(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    with patch("routes.genres.AsyncSession.commit", side_effect=SQLAlchemyError):

        response = await client.post(
            "/stars/", json=payload, headers={"Authorization": f"Bearer {access_token}"}
        )

        assert (
            response.status_code == 500
        ), "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data == {
            "detail": "An error occurred while creating the star."
        }, "Expected message does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_update_star(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"

    star = await db_session.scalar(
        select(StarModel).where(StarModel.name == payload["name"])
    )

    new_payload = {"name": "New test star"}

    new_response = await client.patch(
        f"/stars/{star.id}/",
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
async def test_moder_update_not_existing_star(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "New test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    new_response = await client.patch(
        f"/stars/1000/",
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert (
        new_response.status_code == 404
    ), "Expected status code does not match. Should be 404"
    response_data = new_response.json()
    assert (
        response_data["detail"] == "Star with the given ID was not found."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_update_star(
    client, db_session, reset_db, create_test_user, jwt_manager, create_test_moder
):
    payload = {"name": "Test star"}

    moder_access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/stars/",
        headers={"Authorization": f"Bearer {moder_access_token}"},
        json=payload,
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"

    star = await db_session.scalar(
        select(StarModel).where(StarModel.name == payload["name"])
    )

    new_payload = {"name": "New test star"}

    user_access_token = jwt_manager.create_access_token(
        data={"email": create_test_user.email, "user_id": create_test_user.id}
    )

    response = await client.patch(
        f"/stars/{star.id}/",
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
async def test_moder_update_star_with_same_existing_name(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    stars = await db_session.scalars(
        select(StarModel).where(or_(StarModel.id == 1, StarModel.id == 2))
    )
    stars = stars.all()

    payload = {"name": stars[1].name}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    new_response = await client.patch(
        f"/stars/{stars[0].id}/",
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert (
        new_response.status_code == 409
    ), "Expected status code does not match. Should be 409"
    response_data = new_response.json()
    assert (
        response_data["detail"]
        == f"Star with this name ({payload["name"]}) already exists."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_star_sqlalchemy_error(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    with patch("routes.genres.AsyncSession.commit", side_effect=SQLAlchemyError):

        response = await client.patch(
            "/stars/1/",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert (
            response.status_code == 500
        ), "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data == {
            "detail": "An error occurred while updating the star."
        }, "Expected message does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_delete_star(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"

    star = await db_session.scalar(
        select(StarModel).where(StarModel.name == payload["name"])
    )

    delete_response = await client.delete(
        f"/stars/{star.id}/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        delete_response.status_code == 204
    ), "Expected status code does not match. Should be 204"

    deleted_star = await db_session.scalar(
        select(StarModel).where(StarModel.name == payload["name"])
    )

    assert deleted_star is None, "Star was not deleted"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_delete_star(
    client, db_session, reset_db, create_test_user, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={"email": create_test_user.email, "user_id": create_test_user.id}
    )

    response = await client.delete(
        "/stars/1/", headers={"Authorization": f"Bearer {access_token}"}
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
async def test_moder_delete_star_twice(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.post(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    assert (
        response.status_code == 201
    ), "Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["name"] == payload["name"], "Response data does not match"
    assert "id" in response_data, "Response data does not contain 'id'"

    star = await db_session.scalar(
        select(StarModel).where(StarModel.name == payload["name"])
    )

    first_response = await client.delete(
        f"/stars/{star.id}/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        first_response.status_code == 204
    ), "Expected status code does not match. Should be 204"

    deleted_star = await db_session.scalar(
        select(StarModel).where(StarModel.name == payload["name"])
    )

    assert deleted_star is None, "Star was not deleted"

    second_response = await client.delete(
        f"/stars/{star.id}/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        second_response.status_code == 404
    ), "Expected status code does not match. Should be 404"

    second_response_data = second_response.json()
    assert (
        second_response_data["detail"] == "Star with the given ID was not found."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_delete_not_existing_star(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.delete(
        "/stars/100000/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        response.status_code == 404
    ), "Expected status code does not match. Should be 404"

    second_response_data = response.json()
    assert (
        second_response_data["detail"] == "Star with the given ID was not found."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_moder_delete_star_with_movies(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    response = await client.delete(
        "/stars/1/", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert (
        response.status_code == 409
    ), "Expected status code does not match. Should be 409"

    second_response_data = response.json()
    assert (
        second_response_data["detail"] == "There are already films with this star."
    ), "Response data does not match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_star_sqlalchemy_error(
    client, db_session, reset_db, create_test_moder, jwt_manager
):
    payload = {"name": "Test star"}

    access_token = jwt_manager.create_access_token(
        data={"email": create_test_moder.email, "user_id": create_test_moder.id}
    )

    await client.post(
        "/stars/", headers={"Authorization": f"Bearer {access_token}"}, json=payload
    )

    star = await db_session.scalar(
        select(StarModel).where(StarModel.name == payload["name"])
    )

    with patch("routes.genres.AsyncSession.commit", side_effect=SQLAlchemyError):

        response = await client.delete(
            f"/stars/{star.id}/", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert (
            response.status_code == 500
        ), "Expected status code does not match. Should be 500"
        response_data = response.json()
        assert response_data == {
            "detail": "An error occurred while deleting the star."
        }, "Expected message does not match"
