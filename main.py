from fastapi import FastAPI

from routes.accounts import router as accounts_router
from routes.profiles import router as profiles_router
from routes.movies import router as movies_router
from routes.favorites import router as favorites_router
from routes.genres import router as genres_router

app = FastAPI()

app.include_router(accounts_router, prefix=f"/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix=f"/profiles", tags=["profiles"])
app.include_router(movies_router, prefix=f"/movies", tags=["movies"])
app.include_router(favorites_router, prefix=f"/favorites", tags=["favorites"])
app.include_router(genres_router, prefix=f"/genres", tags=["genres"])