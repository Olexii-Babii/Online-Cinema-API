import pytest
from io import BytesIO
from PIL import Image
from sqlalchemy import select

from database import UserModel, UserProfileModel
from managing.s3_manager import S3Client


@pytest.mark.e2e
@pytest.mark.order(7)
@pytest.mark.asyncio
async def test_create_user_profile(e2e_client, e2e_db_session, settings, s3_client):

    payload = {
        "email": "testuser@example.com",
        "password": "NewPassword12345@"
    }

    user = await e2e_db_session.scalar(select(UserModel).where(UserModel.email == payload["email"]))
    assert user, f"User {payload["email"]} should exist!"

    login_url = "/accounts/login/"
    login_response = await e2e_client.post(login_url, json=payload)
    assert login_response.status_code == 201, "Expected status code does not match. Should be 201"

    tokens = login_response.json()
    access_token = tokens["access_token"]

    img = Image.new("RGB", (100, 100), color="red")
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

    profile_response = await e2e_client.post(profile_url, headers=headers, files=files)
    assert profile_response.status_code == 201, "Expected status code does not match. Should be 201"

    profile_data = profile_response.json()
    assert profile_data["first_name"] == "john"
    assert profile_data["last_name"] == "doe"
    assert profile_data["gender"] == "man"
    assert profile_data["date_of_birth"] == "1990-01-01"
    assert "avatar" in profile_data, "Avatar URL is missing!"

    avatar_key = f"avatars/{user.id}_avatar.jpg"
    expected_url = await s3_client.get_file_url(avatar_key)
    assert profile_data["avatar"] == expected_url, f"Invalid avatar URL: {profile_data['avatar']}"

    profile_db = await e2e_db_session.scalar(select(UserProfileModel).where(UserProfileModel.user_id == user.id))
    assert profile_db, f"Profile for user {user.id} should exist!"
    assert profile_db.avatar, "Avatar path should not be empty!"

    await e2e_db_session.commit()

    storage = S3Client(settings)
    async with storage.session.client(
            "s3", endpoint_url=storage.settings.S3_STORAGE_ENDPOINT
    ) as s3:
        response = await s3.list_objects_v2(
            Bucket=settings.S3_BUCKET_NAME,
            Prefix=avatar_key
        )

    assert "Contents" in response, f"Avatar {avatar_key} was not found in MinIO!"
