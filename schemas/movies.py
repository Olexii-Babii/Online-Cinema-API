import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal


class CertificationResponseSchema(BaseModel):
    id: int
    name: str


class GenresResponseSchema(BaseModel):
    id: int
    name: str


class StarsResponseSchema(BaseModel):
    id: int
    name: str


class DirectorsResponseSchema(BaseModel):
    id: int
    name: str


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    year: int
    time: int
    imdb: float

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int


class MovieCreateSchema(BaseModel):
    name: str = Field(max_length=255)
    year: int = Field(ge=1900)
    time: int = Field(gt=0)
    imdb: float = Field(ge=0, le=10)
    votes: int = Field(ge=0)
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: str
    price: Optional[Decimal] = None
    certification: str
    genres: List[str]
    stars: List[str]
    directors: List[str]



class MovieDetailSchema(BaseModel):
    id: int
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: float
    gross: float
    description: str
    price: Decimal
    certification: CertificationResponseSchema
    genres: List[GenresResponseSchema]
    stars: List[StarsResponseSchema]
    directors: List[DirectorsResponseSchema]


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    year: Optional[int] = None
    time: Optional[int] = None
    imdb: Optional[float] = None
    votes: Optional[int] = None
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None


    @field_validator("name")
    @classmethod
    def name_validation(cls, name: str | None):
        if name is not None:
            if len(name) > 255:
                raise ValueError
            return name

    @field_validator("year")
    @classmethod
    def year_validation(cls, year: int | None):
        if year is not None:
            if year < 1900:
                raise ValueError
            return year

    @field_validator("imdb")
    @classmethod
    def imdb_validation(cls, imdb: float | None):
        if imdb is not None:
            if not (imdb >= 0 and imdb <= 10):
                raise ValueError
            return imdb


    @field_validator("time")
    @classmethod
    def time_validation(cls, time: int | None):
        if time is not None:
            if not time >= 0:
                raise ValueError
            return time

    @field_validator("price")
    @classmethod
    def price_validation(cls, price: Decimal | None):
        if price is not None:
            if not price >= 0:
                raise ValueError
            return price

    @field_validator("votes")
    @classmethod
    def votes_validation(cls, votes: int | None):
        if votes is not None:
            if not votes >= 0:
                raise ValueError
            return votes


class ReactionRequestSchema(BaseModel):
    value: int

    @field_validator("value")
    @classmethod
    def value_validation(cls, value: int):
        if value not in (1, -1, 0):
            raise ValueError
        return value


class CommentRequestSchema(BaseModel):
    text: str


class CommentResponseSchema(BaseModel):
    id: int
    text: str
    user_id: int
    movie_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class CommentReplyRequestSchema(BaseModel):
    text: str
    parent_id: int


class CommentReplyResponseSchema(BaseModel):
    id: int
    text: str
    user_id: int
    movie_id: int
    parent_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class MovieSortField(str, Enum):
    ID = "id"
    NAME = "name"
    PRICE = "price"
    YEAR = "year"
    IMDB = "imdb"



class MovieFilterSchema(BaseModel):
    search: Optional[str] = Field(None, min_length=1, max_length=100, description="Search by movie name")

    genres: Optional[str] = Field(None, description="Filter by genres (comma-separated)")


    year: Optional[int] = Field(None, ge=1900, le=2030, description="Exact year")
    year_from: Optional[int] = Field(None, ge=1900, le=2030, description="Year from")
    year_to: Optional[int] = Field(None, ge=1900, le=2030, description="Year to")

    imdb_min: Optional[float] = Field(None, ge=0, le=10, description="Minimum IMDB rating")
    imdb_max: Optional[float] = Field(None, ge=0, le=10, description="Maximum IMDB rating")


    directors: Optional[str] = Field(None, description="Filter by directors (comma-separated)")

    stars: Optional[str] = Field(None, description="Filter by stars (comma-separated)")

    price_min: Optional[float] = Field(None, ge=0, description="Minimum price")
    price_max: Optional[float] = Field(None, ge=0, description="Maximum price")

    sort_by: Optional[MovieSortField] = Field(
        MovieSortField.ID,
        description="Field to sort by"
    )
    order: SortOrder = Field(
        SortOrder.DESC,
        description="Sort order (asc or desc)"
    )

    @field_validator("year_to")
    def validate_year_range(cls, v, values):
        if v and "year_from" in values.data and values.data["year_from"]:
            if v < values.data["year_from"]:
                raise ValueError("year_to must be greater than or equal to year_from")
        return v

    @field_validator("imdb_max")
    def validate_imdb_range(cls, v, values):
        if v and "imdb_min" in values.data and values.data["imdb_min"]:
            if v < values.data["imdb_min"]:
                raise ValueError("imdb_max must be greater than or equal to imdb_min")
        return v


class RatingRequestSchema(BaseModel):
    value: int = Field(ge=0, le=10)


class StarsRequestSchema(BaseModel):
    name: str
