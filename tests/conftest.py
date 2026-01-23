import datetime
import json

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_settings, get_s3_client
from database import UserGroupEnum, UserGroupModel, CertificationModel, GenreModel, StarModel, DirectorModel, UserModel, \
    UserProfileModel, MovieModel, FavoriteModel, MovieReactionModel, ActivationTokenModel
from database.engine import reset_database, get_db_contextmanager
from database.models.favorites import MoviesFavoritesModel
from database.models.movies import MovieRatingModel, MovieCommentModel, MoviesGenresModel, StarsMoviesModel, \
    MoviesDirectorsModel
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

    with open("tests/seed_test_data.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    user_groups = [UserGroupModel(**ug) for ug in data["user_groups"]]
    certifications = [CertificationModel(**c) for c in data["certifications"]]
    genres = [GenreModel(**g) for g in data["genres"]]
    stars = [StarModel(**s) for s in data["stars"]]
    directors = [DirectorModel(**d) for d in data["directors"]]

    db_session.add_all(user_groups + certifications + genres + stars + directors)
    await db_session.flush()

    users = [UserModel(**u) for u in data["users"]]
    movies = [MovieModel(**m) for m in data["movies"]]

    db_session.add_all(users + movies)
    await db_session.flush()

    users_profiles = []
    for user_profile in data["user_profiles"]:
        users_profiles.append(
            UserProfileModel(
                id=user_profile["id"],
                first_name=user_profile["first_name"],
                last_name=user_profile["last_name"],
                avatar=user_profile["avatar"],
                gender=user_profile["gender"],
                date_of_birth=datetime.datetime.strptime(
                    user_profile["date_of_birth"],
                    "%Y-%m-%d"
                ).date() if user_profile["date_of_birth"] else None,
                info=user_profile["info"],
                user_id=user_profile["user_id"]
            )
        )
    favorites = [FavoriteModel(**f) for f in data["favorites"]]
    reactions = [MovieReactionModel(**r) for r in data["movie_reactions"]]
    ratings = [MovieRatingModel(**r) for r in data["movie_ratings"]]
    comments = [MovieCommentModel(**c) for c in data["movie_comments"]]

    db_session.add_all(users_profiles + favorites + reactions + ratings + comments)

    await db_session.execute(MoviesGenresModel.insert(), data["movie_genres"])
    await db_session.execute(StarsMoviesModel.insert(), data["movie_stars"])
    await db_session.execute(MoviesDirectorsModel.insert(), data["movie_directors"])
    await db_session.execute(MoviesFavoritesModel.insert(), data["movie_favorites"])

    await db_session.flush()
    await db_session.commit()

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