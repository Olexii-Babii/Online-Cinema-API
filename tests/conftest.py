from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_settings, get_s3_client
from database import UserGroupEnum, UserGroupModel, UserModel
from database import reset_database, get_db_contextmanager
from database.populate_db import populate_db
from main import app
from managing.jwt_manager import JWTAuthManager
from managing.s3_manager import S3Client
from tests.fakes.email_sender import FakeEmailSender
from tests.fakes.s3_manager import FakeS3Client


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "order: Specify the order of test execution"
    )
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )


@pytest_asyncio.fixture(scope="function", autouse=True)
async def reset_db(request):
    if "e2e" in request.keywords:
        yield
    else:
        await reset_database()
        yield


@pytest_asyncio.fixture(scope="session")
async def reset_db_once_for_e2e(request):
    await reset_database()


@pytest_asyncio.fixture(scope="session")
async def settings():
    return get_settings()


@pytest_asyncio.fixture(scope="function")
async def email_sender_fake():
    return FakeEmailSender()


@pytest_asyncio.fixture(scope="function")
async def s3_storage_fake():
    return FakeS3Client()


@pytest_asyncio.fixture(scope="session")
async def s3_client(settings):
    return S3Client(
        settings=settings
    )

@pytest_asyncio.fixture(scope="function")
async def client(s3_storage_fake):
    app.dependency_overrides[get_s3_client] = lambda: s3_storage_fake

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session")
async def e2e_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with get_db_contextmanager() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def e2e_db_session():
    async with get_db_contextmanager() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def jwt_manager():
    settings = get_settings()
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


@pytest_asyncio.fixture(scope="function")
async def seed_user_groups(db_session: AsyncSession):
    groups = [{"name": group.value} for group in UserGroupEnum]
    await db_session.execute(insert(UserGroupModel).values(groups))
    await db_session.commit()
    yield db_session


@pytest_asyncio.fixture(scope="function")
async def seed_database(db_session):
    await populate_db(db_session=db_session)
    yield db_session


@pytest_asyncio.fixture(scope="function")
async def create_test_user(db_session: AsyncSession, seed_database):
    payload = {
        "email": "testuser@example.com",
        "password": "Password12345@"
    }

    user_group = await db_session.scalar(select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER))

    user = UserModel(
        email=payload["email"],
        password=payload["password"],
        group_id=user_group.id
    )
    user.is_active = True

    db_session.add(user)
    await db_session.commit()

    yield user


@pytest_asyncio.fixture(scope="function")
async def create_test_moder(db_session: AsyncSession, seed_database):
    payload = {
        "email": "testmoder@example.com",
        "password": "Password12345@"
    }

    moder_group = await db_session.scalar(select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.MODERATOR))

    moder = UserModel(
        email=payload["email"],
        password=payload["password"],
        group_id=moder_group.id
    )
    moder.is_active = True

    db_session.add(moder)
    await db_session.commit()

    yield moder


@pytest.fixture(autouse=True)
def mock_celery_tasks():
    with patch("routes.accounts.delay_delete_activation_token.apply_async") as mocked_task:
        yield mocked_task
