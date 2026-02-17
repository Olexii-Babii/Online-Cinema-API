from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from io import BytesIO
from PIL import Image
from sqlalchemy import select, func

from database import UserModel, UserProfileModel, UserGroupModel, UserGroupEnum


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_user_profile_with_fake_s3(
    db_session, seed_user_groups, reset_db, jwt_manager, s3_storage_fake, client
):
    payload = {"email": "testuser@emaple.com", "password": "Password12345@"}
    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    user = UserModel(
        email=payload["email"], password=payload["password"], group_id=user_group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == payload["email"])
    )

    access_token = jwt_manager.create_access_token({"user_id": user.id})

    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    avatar_key = f"avatars/{user.id}_avatar.jpg"
    profile_url = f"/profiles/users/{user.id}/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "This is a test profile."),
        "avatar": ("avatar.jpg", img_bytes, "image/jpeg"),
    }

    response = await client.post(profile_url, headers=headers, files=files)
    assert (
        response.status_code == 201
    ), f"Expected status code does not match. Should be 201"
    profile_data = response.json()

    assert profile_data["first_name"] == "john", "First name does not match."
    assert profile_data["last_name"] == "doe", "Last name does not match."
    assert profile_data["gender"] == "man", "Gender does not match."
    assert (
        profile_data["date_of_birth"] == "1990-01-01"
    ), "Date of birth does not match."
    assert "avatar" in profile_data, "Avatar URL is missing!"

    assert (
        avatar_key in s3_storage_fake.storage
    ), "Avatar file was not uploaded to Fake S3 Storage!"
    expected_url = f"http://fake-s3.local/{avatar_key}"
    actual_url = await s3_storage_fake.get_file_url(avatar_key)
    assert actual_url == expected_url, "Avatar URL does not match expected URL."

    profile = await db_session.scalar(
        select(UserProfileModel).where(UserProfileModel.user_id == user.id)
    )
    assert profile, f"Profile for user {user.id} should exist!"

    assert profile.first_name == "john", "First name is incorrect!"
    assert profile.last_name == "doe", "Last name is incorrect!"
    assert profile.gender == "man", "Gender is incorrect!"
    assert str(profile.date_of_birth) == "1990-01-01", "Date of birth is incorrect!"
    assert profile.info == "This is a test profile.", "Profile info is incorrect!"
    assert profile.avatar == avatar_key, "Avatar key in database does not match!"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize(
    "headers, expected_status, expected_detail",
    [
        (None, 401, "Authorization header is missing"),
        (
            {"Authorization": "Token invalid_token"},
            401,
            "Invalid Authorization header format. Expected 'Bearer <token>'",
        ),
    ],
)
async def test_create_user_profile_invalid_auth(
    client, headers, expected_status, expected_detail
):

    profile_url = "/profiles/users/1/profile/"
    response = await client.post(profile_url, headers=headers)
    assert (
        response.status_code == expected_status
    ), f"Expected {expected_status}, got {response.status_code}"
    assert (
        response.json()["detail"] == expected_detail
    ), f"Unexpected error message: {response.json()['detail']}"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_user_profile_expired_token(client, jwt_manager):

    expired_time = datetime.now() - timedelta(days=1)
    with patch("managing.jwt_manager.datetime") as mock_datetime:
        mock_datetime.now.return_value = expired_time
        expired_token = jwt_manager.create_access_token({"user_id": 1})

    profile_url = "/profiles/users/1/profile/"
    headers = {"Authorization": f"Bearer {expired_token}"}

    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "Test profile."),
        "avatar": ("avatar.jpg", img_bytes, "image/jpeg"),
    }

    response = await client.post(profile_url, headers=headers, files=files)

    assert (
        response.status_code == 401
    ), f"Expected status code does not match. Should be 401"
    assert (
        response.json()["detail"] == "Token has expired."
    ), f"Unexpected error message: {response.json()['detail']}"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_admin_creates_user_profile(
    db_session, seed_user_groups, reset_db, jwt_manager, s3_storage_fake, client
):
    user_payload = {"email": "testuser@emaple.com", "password": "UserPassword12345@"}

    admin_payload = {"email": "testadmin@emaple.com", "password": "AdminPassword12345@"}

    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )

    admin_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.ADMIN)
    )

    admin = UserModel(
        email=admin_payload["email"],
        password=admin_payload["password"],
        group_id=admin_group.id,
    )
    admin.is_active = True
    db_session.add(admin)

    user = UserModel(
        email=user_payload["email"],
        password=user_payload["password"],
        group_id=user_group.id,
    )
    user.is_active = True
    db_session.add(user)

    await db_session.commit()

    users = await db_session.scalars(
        select(UserModel).where(
            UserModel.email.in_([user_payload["email"], admin_payload["email"]])
        )
    )

    users_dict = {user.email: user for user in users}

    admin_user = users_dict[admin_payload["email"]]
    regular_user = users_dict[user_payload["email"]]

    admin_token = jwt_manager.create_access_token({"user_id": admin_user.id})

    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    avatar_key = f"avatars/{regular_user.id}_avatar.jpg"
    profile_url = f"/profiles/users/{regular_user.id}/profile/"
    headers = {"Authorization": f"Bearer {admin_token}"}
    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "Test profile."),
        "avatar": ("avatar.jpg", img_bytes, "image/jpeg"),
    }

    response = await client.post(profile_url, headers=headers, files=files)
    assert (
        response.status_code == 201
    ), f"Expected status code does not match. Should be 201"
    profile_data = response.json()

    assert profile_data["first_name"] == "john"
    assert profile_data["last_name"] == "doe"
    assert profile_data["gender"] == "man"
    assert profile_data["date_of_birth"] == "1990-01-01"
    assert "avatar" in profile_data, "Avatar URL is missing!"

    assert (
        avatar_key in s3_storage_fake.storage
    ), "Avatar file was not uploaded to Fake S3 Storage!"
    expected_url = f"http://fake-s3.local/{avatar_key}"
    actual_url = await s3_storage_fake.get_file_url(avatar_key)
    assert actual_url == expected_url, "Avatar URL does not match expected URL."

    profile = await db_session.scalar(
        select(UserProfileModel).where(UserProfileModel.user_id == regular_user.id)
    )
    assert profile, f"Profile for user {regular_user.id} should exist!"

    assert profile.first_name == "john", "First name is incorrect!"
    assert profile.last_name == "doe", "Last name is incorrect!"
    assert profile.gender == "man", "Gender is incorrect!"
    assert str(profile.date_of_birth) == "1990-01-01", "Date of birth is incorrect!"
    assert profile.info == "Test profile.", "Profile info is incorrect!"
    assert profile.avatar == avatar_key, "Avatar key in database does not match!"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_user_cannot_create_another_user_profile(
    db_session, seed_user_groups, reset_db, jwt_manager, s3_storage_fake, client
):
    user1_payload = {"email": "testuser1@emaple.com", "password": "User1Password12345@"}

    user2_payload = {"email": "testuser2@emaple.com", "password": "User2Password12345@"}

    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )

    user_1 = UserModel(
        email=user1_payload["email"],
        password=user1_payload["password"],
        group_id=user_group.id,
    )
    user_1.is_active = True
    db_session.add(user_1)

    user_2 = UserModel(
        email=user2_payload["email"],
        password=user2_payload["password"],
        group_id=user_group.id,
    )
    user_2.is_active = True
    db_session.add(user_2)

    await db_session.commit()

    users = await db_session.scalars(
        select(UserModel).where(
            UserModel.email.in_([user1_payload["email"], user2_payload["email"]])
        )
    )

    users_dict = {user.email: user for user in users}
    user_1 = users_dict[user1_payload["email"]]
    user_2 = users_dict[user2_payload["email"]]

    user_1_token = jwt_manager.create_access_token({"user_id": user_1.id})

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    profile_url = f"/profiles/users/{user_2.id}/profile/"
    headers = {"Authorization": f"Bearer {user_1_token}"}
    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "Attempting unauthorized profile creation."),
        "avatar": ("avatar.jpg", img_bytes, "image/jpeg"),
    }

    response = await client.post(profile_url, headers=headers, files=files)
    assert (
        response.status_code == 403
    ), f"Expected status code does not match. Should be 403"
    assert (
        response.json()["detail"] == "You don't have permission to edit this profile."
    ), f"Unexpected error message: {response.json()['detail']}"

    profile = await db_session.scalar(
        select(UserProfileModel).where(UserProfileModel.user_id == user_2.id)
    )
    assert profile is None, "Profile should not have been created!"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_inactive_user_cannot_create_profile(
    db_session, seed_user_groups, reset_db, jwt_manager, s3_storage_fake, client
):
    payload = {"email": "inactive@example.com", "password": "Password12345@"}

    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )

    user = UserModel(
        email=payload["email"], password=payload["password"], group_id=user_group.id
    )
    user.is_active = False
    db_session.add(user)
    await db_session.commit()

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == payload["email"])
    )
    access_token = jwt_manager.create_access_token({"user_id": user.id})

    img = Image.new("RGB", (100, 100), color="gray")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    profile_url = f"/profiles/users/{user.id}/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "Attempting to create a profile while inactive."),
        "avatar": ("avatar.jpg", img_bytes, "image/jpeg"),
    }

    response = await client.post(profile_url, headers=headers, files=files)
    assert (
        response.status_code == 401
    ), f"Expected status code does not match. Should be 401"
    assert (
        response.json()["detail"] == "User not found or not active."
    ), f"Unexpected error message: {response.json()['detail']}"

    profile = await db_session.scalar(
        select(UserProfileModel).where(UserProfileModel.user_id == user.id)
    )
    assert profile is None, "Profile should not have been created!"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cannot_create_profile_twice(
    db_session, seed_user_groups, reset_db, jwt_manager, s3_storage_fake, client
):
    payload = {"email": "testuser@example.com", "password": "Password12345@"}

    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )

    user = UserModel(
        email=payload["email"], password=payload["password"], group_id=user_group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    access_token = jwt_manager.create_access_token({"user_id": user.id})

    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    profile_url = f"/profiles/users/{user.id}/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "This is a test profile."),
        "avatar": ("avatar.jpg", img_bytes, "image/jpeg"),
    }

    response1 = await client.post(profile_url, headers=headers, files=files)
    assert (
        response1.status_code == 201
    ), f"Expected status code does not match. Should be 201"

    response2 = await client.post(profile_url, headers=headers, files=files)
    assert (
        response2.status_code == 400
    ), f"Expected status code does not match. Should be 400"
    assert (
        response2.json()["detail"] == "User already has a profile."
    ), f"Unexpected error message: {response2.json()['detail']}"

    count = await db_session.scalar(
        select(func.count(UserProfileModel.id)).where(
            UserProfileModel.user_id == user.id
        )
    )
    assert count == 1, f"Expected only one profile, but found {count}"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_profile_creation_fails_on_s3_upload_error(
    db_session, seed_user_groups, reset_db, jwt_manager, s3_storage_fake, client
):
    payload = {"email": "testuser@example.com", "password": "Password12345@"}

    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )

    user = UserModel(
        email=payload["email"], password=payload["password"], group_id=user_group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    access_token = jwt_manager.create_access_token({"user_id": user.id})

    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    profile_url = f"/profiles/users/{user.id}/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "This is a test profile."),
        "avatar": ("avatar.jpg", img_bytes, "image/jpeg"),
    }

    with patch.object(
        s3_storage_fake,
        "upload_image",
        side_effect=ConnectionError("Simulated S3 failure"),
    ):
        response = await client.post(profile_url, headers=headers, files=files)

    assert (
        response.status_code == 500
    ), f"Expected status code does not match. Should be 500"
    assert (
        response.json()["detail"] == "Failed to upload avatar. Please try again later."
    ), f"Unexpected error message: {response.json()['detail']}"

    profile = await db_session.scalar(
        select(UserProfileModel).where(UserProfileModel.user_id == user.id)
    )
    assert profile is None, "Profile should not be created when S3 upload fails!"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize(
    "first_name, last_name, expected_error",
    [
        ("John!", "Doe", "John! contains non-english letters"),
        ("John", "Doe!", "Doe! contains non-english letters"),
    ],
)
async def test_profile_creation_invalid_name(
    client, jwt_manager, first_name, last_name, expected_error
):

    access_token = jwt_manager.create_access_token({"user_id": 1})

    profile_url = "/profiles/users/1/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {
        "first_name": (None, first_name),
        "last_name": (None, last_name),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "This is a test profile."),
        "avatar": ("avatar.jpg", BytesIO(b"fake_image"), "image/jpeg"),
    }

    response = await client.post(profile_url, headers=headers, files=files)

    assert (
        response.status_code == 422
    ), f"Expected status code does not match. Should be 422"
    assert expected_error in str(
        response.json()
    ), f"Unexpected error message: {response.json()}"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_profile_creation_invalid_gender(client, jwt_manager):

    access_token = jwt_manager.create_access_token({"user_id": 1})

    profile_url = "/profiles/users/1/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "other"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "This is a test profile."),
        "avatar": ("avatar.jpg", BytesIO(b"fake_image"), "image/jpeg"),
    }

    response = await client.post(profile_url, headers=headers, files=files)

    assert (
        response.status_code == 422
    ), f"Expected status code does not match. Should be 422"
    assert "Gender must be either 'man' or 'woman'" in str(
        response.json()
    ), f"Unexpected error message: {response.json()}"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize(
    "birth_date, expected_error",
    [
        ("1800-01-01", "Date must be greater than 1900."),
        ("2010-01-01", "Age must be greater than 18 years."),
    ],
)
async def test_profile_creation_invalid_birth_date(
    client, jwt_manager, birth_date, expected_error
):

    access_token = jwt_manager.create_access_token({"user_id": 1})
    profile_url = "/profiles/users/1/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, birth_date),
        "info": (None, "This is a test profile."),
        "avatar": ("avatar.jpg", BytesIO(b"fake_image"), "image/jpeg"),
    }

    response = await client.post(profile_url, headers=headers, files=files)
    assert (
        response.status_code == 422
    ), f"Expected status code does not match. Should be 422"
    assert expected_error in str(
        response.json()
    ), f"Unexpected error message: {response.json()}"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize("info_value", ["", "   "])
async def test_profile_creation_empty_info(client, jwt_manager, info_value):

    access_token = jwt_manager.create_access_token({"user_id": 1})
    profile_url = "/profiles/users/1/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, info_value),
        "avatar": ("avatar.jpg", BytesIO(b"fake_image"), "image/jpeg"),
    }

    response = await client.post(profile_url, headers=headers, files=files)
    assert (
        response.status_code == 422
    ), f"Expected status code does not match. Should be 422"
    assert "Info field cannot be empty or contain only spaces." in str(
        response.json()
    ), f"Unexpected error message: {response.json()}"
