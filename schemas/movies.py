from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import DECIMAL


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
    price: Optional[DECIMAL] = None
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
    price: DECIMAL
    certification: CertificationResponseSchema
    genres: List[GenresResponseSchema]
    stars: List[StarsResponseSchema]
    directors: List[DirectorsResponseSchema]


