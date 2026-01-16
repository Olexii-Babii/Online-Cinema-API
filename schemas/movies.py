from typing import List

from pydantic import BaseModel



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