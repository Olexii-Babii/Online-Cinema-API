import os

from database.models.base import Base
from database.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserProfileModel
)
from database.models.movies import (
    MovieModel,
    GenreModel,
    StarModel,
    DirectorModel,
    CertificationModel,
    MovieReactionModel,
)

from database.models.favorites import FavoriteModel

environment = os.getenv("ENVIRONMENT", "developing")

if environment == "testing":
    from database.sqlite_engine import (
        get_sqlite_db_contextmanager as get_db_contextmanager,
        get_sqlite_db as get_db
    )
else:
    from database.postgre_engine import (
        get_postgresql_db_contextmanager as get_db_contextmanager,
        get_postgresql_db as get_db
    )

from database.sqlite_engine import reset_database
