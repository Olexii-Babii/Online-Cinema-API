import asyncio
import json
import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import UserGroupModel, CertificationModel, GenreModel, StarModel, DirectorModel, UserModel, MovieModel, \
    UserProfileModel, FavoriteModel, MovieReactionModel
from database.models.favorites import MoviesFavoritesModel
from database.models.movies import MovieRatingModel, MovieCommentModel, MoviesGenresModel, StarsMoviesModel, \
    MoviesDirectorsModel
from database import get_db_contextmanager


async def populate_db(db_session: AsyncSession):
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
    await db_session.flush()

    await db_session.execute(MoviesGenresModel.insert(), data["movie_genres"])
    await db_session.execute(StarsMoviesModel.insert(), data["movie_stars"])
    await db_session.execute(MoviesDirectorsModel.insert(), data["movie_directors"])
    await db_session.execute(MoviesFavoritesModel.insert(), data["movie_favorites"])

    await db_session.flush()
    await db_session.commit()


async def check_is_empty_db(db_session: AsyncSession):
    result = await db_session.execute(select(MovieModel).limit(1))
    first_movie = result.scalars().first()
    return first_movie is None


async def main():
    async with get_db_contextmanager() as db_session:
        if await check_is_empty_db(db_session=db_session):
            try:
                await populate_db(db_session=db_session)
                print("Database populated successfully")
            except Exception as e:
                print(f"Database failed to populate: {e}")
        else:
            print("Database already populated")


if __name__ == "__main__":
    asyncio.run(main())
