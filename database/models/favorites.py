from sqlalchemy import ForeignKey, UniqueConstraint, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

MoviesFavoritesModel = Table(
    "movie_favorites",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "favorite_id",
        ForeignKey("favorites.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


class FavoriteModel(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel", secondary=MoviesFavoritesModel, back_populates="favorites"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="favorite"
    )

