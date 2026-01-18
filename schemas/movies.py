import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
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