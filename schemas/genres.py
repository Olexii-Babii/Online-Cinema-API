from pydantic import BaseModel


class GenresCountResponseSchema(BaseModel):
    name: str
    movie_count: int


class GenresRequestSchema(BaseModel):
    name: str
