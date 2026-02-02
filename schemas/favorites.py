from pydantic import BaseModel


class FavoriteMovieResponseSchema(BaseModel):
    movie_id: int
    message: str
