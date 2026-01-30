import base64
import re

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from validators import url as validate_url
import pytest
import httpx

from database import (
    ActivationTokenModel,
    UserModel,
    RefreshTokenModel,
    PasswordResetTokenModel
)


@pytest.mark.e2e
@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_registration(e2e_client, reset_db_once_for_e2e, settings, seed_user_groups, e2e_db_session):
    payload = {
        "email": "testuser@example.com",
        "password": "Password12345@"
    }

    response = await e2e_client.post("/accounts/register/", json=payload)
    assert response.status_code == 201, f"Expected status code does not match. Should be 201"
    response_data = response.json()
    assert response_data["email"] == payload["email"]

    mailhog_url = f"http://{settings.MAIL_SERVER}:{settings.MAIL_API_PORT}/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)

    await e2e_db_session.commit()
    e2e_db_session.expire_all()

    assert mailhog_response.status_code == 200, f"Expected status code does not match. Should be 200"
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No emails were sent!"

    email = messages[0]
    assert payload["email"] in email["Content"]["Headers"]["To"][0], "Recipient email does not match!"

    email_subject = email["Content"]["Headers"].get("Subject", [None])[0]
    assert email_subject == "Activate your account", f"Expected subject 'Activate your account', but got '{email_subject}'"
    raw_letter = email["Content"]["Body"]

    lines = raw_letter.split("\n")
    base64_start = False
    raw_text = []

    for line in lines:
        if line.strip() == '' and not base64_start:
            base64_start = True
            continue
        if base64_start and line.startswith('--'):
            break
        if base64_start and line.strip():
            raw_text.append(line.strip())
    raw_text = "".join(raw_text)
    email_text = base64.b64decode(raw_text).decode('utf-8')

    pattern = rf"{settings.BASE_URL}/accounts/activate\?token=([\w\.\-\=]+)"
    match = re.search(pattern, email_text)

    assert match is not None, "Activation link not found in the email text!"
    activation_url = match.group(0)

    assert validate_url(activation_url), f"The extracted URL '{activation_url}' is not valid!"


@pytest.mark.e2e
@pytest.mark.order(2)
@pytest.mark.asyncio
async def test_account_activation(e2e_client, settings, e2e_db_session):
    payload = {
        "email": "testuser@example.com"
    }

    activation_token_record = await e2e_db_session.scalar(select(ActivationTokenModel)
                                                          .join(UserModel)
                                                          .where(UserModel.email == payload["email"]))
    assert activation_token_record, f"Activation token for email {payload['email']} not found!"
    token_value = activation_token_record.token

    activation_url = "/accounts/activate/"
    response = await e2e_client.post(activation_url, json={"email": payload["email"], "token": token_value})
    assert response.status_code == 200, f"Expected status code does not match. Should be 200"
    response_data = response.json()
    assert response_data["message"] == "User account activated successfully.", "Unexpected activation message!"

    await e2e_db_session.commit()

    activated_user = await e2e_db_session.scalar(select(UserModel).where(UserModel.email == payload["email"]))
    assert activated_user.is_active, f"User {payload["email"]} is not active!"

    mailhog_url = f"http://{settings.MAIL_SERVER}:{settings.MAIL_API_PORT}/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    assert mailhog_response.status_code == 200, "Expected status code does not match. Should be 200"
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No emails were sent!"

    email = messages[0]
    assert payload["email"] in email["Content"]["Headers"]["To"][0], "Recipient email does not match!"
    email_subject = email["Content"]["Headers"].get("Subject", [None])[0]
    assert email_subject == "Account Activated Successfully", \
        f"Expected subject 'Account Activated Successfully', but got '{email_subject}'"

    raw_letter = email["Content"]["Body"]

    lines = raw_letter.split("\n")
    base64_start = False
    raw_text = []

    for line in lines:
        if line.strip() == '' and not base64_start:
            base64_start = True
            continue
        if base64_start and line.startswith('--'):
            break
        if base64_start and line.strip():
            raw_text.append(line.strip())
    raw_text = "".join(raw_text)
    email_text = base64.b64decode(raw_text).decode('utf-8')

    pattern = rf"{settings.BASE_URL}/accounts/login/"
    match = re.search(pattern, email_text)

    assert match is not None, "Login link not found in the email text!"
    activation_complete_url = match.group(0)

    assert validate_url(activation_complete_url), f"The extracted URL '{activation_complete_url}' is not valid!"


@pytest.mark.e2e
@pytest.mark.order(3)
@pytest.mark.asyncio
async def test_user_login(e2e_client, e2e_db_session):
    payload = {
        "email": "testuser@example.com",
        "password": "Password12345@"
    }

    login_url = "/accounts/login/"
    response = await e2e_client.post(login_url, json=payload)

    assert response.status_code == 201, "Expected status code does not match. Should be 200"
    response_data = response.json()

    assert "access_token" in response_data, "Access token is missing in the response!"
    assert "refresh_token" in response_data, "Refresh token is missing in the response!"

    refresh_token = response_data["refresh_token"]

    stored_token = await e2e_db_session.scalar(select(RefreshTokenModel)
                                               .options(joinedload(RefreshTokenModel.user))
                                               .where(RefreshTokenModel.token == refresh_token))

    assert stored_token is not None, "Refresh token was not stored in the database!"
    assert stored_token.user.email == payload["email"], "Refresh token is linked to the wrong user!"


@pytest.mark.e2e
@pytest.mark.order(4)
@pytest.mark.asyncio
async def test_request_password_reset(e2e_client, e2e_db_session, settings):

    email = "testuser@example.com"
    reset_url = "/accounts/password-reset/request/"

    response = await e2e_client.post(reset_url, json={"email": email})
    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    response_data = response.json()
    assert response_data["message"] == "If you are registered, you will receive an email with instructions."

    reset_token = await e2e_db_session.scalar(
        select(PasswordResetTokenModel)
        .join(UserModel)
        .where(UserModel.email == email))
    assert reset_token, f"Password reset token for email {email} was not created!"

    mailhog_url = f"http://{settings.MAIL_SERVER}:{settings.MAIL_API_PORT}/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)

    assert mailhog_response.status_code == 200, "Expected status code does not match. Should be 200"
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No emails were sent!"

    email_data = messages[0]
    assert email in email_data["Content"]["Headers"]["To"][0], "Recipient email does not match!"
    email_subject = email_data["Content"]["Headers"].get("Subject", [None])[0]
    assert email_subject == "Reset your password", \
        f"Expected subject 'Reset your password', but got '{email_subject}'"

    raw_letter = email_data["Content"]["Body"]

    lines = raw_letter.split("\n")
    base64_start = False
    raw_text = []

    for line in lines:
        if line.strip() == '' and not base64_start:
            base64_start = True
            continue
        if base64_start and line.startswith('--'):
            break
        if base64_start and line.strip():
            raw_text.append(line.strip())
    raw_text = "".join(raw_text)
    email_text = base64.b64decode(raw_text).decode('utf-8')

    pattern = rf"{settings.BASE_URL}/accounts/reset-password\?token=([\w\.\-\=]+)"
    match = re.search(pattern, email_text)

    assert match is not None, "Reset link not found in the email text!"
    reset_url = match.group(0)

    assert validate_url(reset_url), f"The extracted URL '{reset_url}' is not valid!"


@pytest.mark.e2e
@pytest.mark.order(5)
@pytest.mark.asyncio
async def test_reset_password(e2e_client, e2e_db_session, settings):
    payload = {
        "email": "testuser@example.com",
        "password": "NewPassword12345@",
    }
    reset_token_record = await e2e_db_session.scalar(
        select(PasswordResetTokenModel)
        .join(UserModel)
        .where(UserModel.email == payload["email"]))

    assert reset_token_record, f"Password reset token for email {payload["email"]} was not found!"
    reset_token = reset_token_record.token
    payload["token"] = reset_token

    reset_url = "/accounts/reset-password/complete/"
    response = await e2e_client.post(reset_url, json=payload)

    assert response.status_code == 200, "Expected status code does not match. Should be 200"
    response_data = response.json()
    assert response_data["message"] == "Password reset successfully.", "Unexpected password reset message!"

    deleted_token = await e2e_db_session.scalar(select(PasswordResetTokenModel)
                                                .where(PasswordResetTokenModel.user_id == reset_token_record.user_id ))
    assert deleted_token is None, "Password reset token was not deleted after use!"

    updated_user = await e2e_db_session.scalar(select(UserModel).where(UserModel.email == payload["email"]))
    assert updated_user is not None, f"User with email {payload["email"]} not found!"
    assert updated_user.verify_password(payload["password"]), "Password was not updated successfully!"

    await e2e_db_session.commit()

    mailhog_url = f"http://{settings.MAIL_SERVER}:{settings.MAIL_API_PORT}/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)

    assert mailhog_response.status_code == 200, "Expected status code does not match. Should be 200"
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No emails were sent!"

    email_data = messages[0]
    assert payload["email"] in email_data["Content"]["Headers"]["To"][0], "Recipient email does not match!"
    email_subject = email_data["Content"]["Headers"].get("Subject", [None])[0]
    assert email_subject == "Password Changed Successfully", \
        f"Expected subject 'Password Changed Successfully', but got '{email_subject}'"

    raw_letter = email_data["Content"]["Body"]

    lines = raw_letter.split("\n")
    base64_start = False
    raw_text = []

    for line in lines:
        if line.strip() == '' and not base64_start:
            base64_start = True
            continue
        if base64_start and line.startswith('--'):
            break
        if base64_start and line.strip():
            raw_text.append(line.strip())
    raw_text = "".join(raw_text)
    email_text = base64.b64decode(raw_text).decode('utf-8')

    pattern = rf"{settings.BASE_URL}/accounts/login/"
    match = re.search(pattern, email_text)

    assert match is not None, "Login link not found in the email text!"
    reset_complete_url = match.group(0)

    assert validate_url(reset_complete_url), f"The extracted URL '{reset_complete_url}' is not valid!"


@pytest.mark.e2e
@pytest.mark.order(6)
@pytest.mark.asyncio
async def test_user_login_with_new_password(e2e_client, e2e_db_session):

    payload = {
        "email": "testuser@example.com",
        "password": "NewPassword12345@"
    }

    login_url = "/accounts/login/"
    response = await e2e_client.post(login_url, json=payload)
    assert response.status_code == 201, f"Expected status code does not match. Should be 201"

    response_data = response.json()
    assert "access_token" in response_data, "Access token is missing in response!"
    assert "refresh_token" in response_data, "Refresh token is missing in response!"

    refresh_token = response_data["refresh_token"]

    stored_token = await e2e_db_session.scalar(select(RefreshTokenModel).options(joinedload(RefreshTokenModel.user)).where(RefreshTokenModel.token == refresh_token))
    assert stored_token is not None, "Refresh token was not stored in the database!"
    assert stored_token.user.email == payload["email"], "Refresh token is linked to the wrong user!"