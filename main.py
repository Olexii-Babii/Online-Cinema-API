import secrets

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from routes.accounts import router as accounts_router
from routes.profiles import router as profiles_router
from routes.movies import router as movies_router
from routes.favorites import router as favorites_router
from routes.genres import router as genres_router
from routes.stars import router as stars_router

app = FastAPI(
    title="Online Cinema API",
    description="API for streaming service",
    version="1.0.0",
    openapi_version="3.1.0",
    docs_url=None,
    redoc_url=None)


security = HTTPBasic()

app.include_router(accounts_router, prefix=f"/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix=f"/profiles", tags=["profiles"])
app.include_router(movies_router, prefix=f"/movies", tags=["movies"])
app.include_router(favorites_router, prefix=f"/favorites", tags=["favorites"])
app.include_router(genres_router, prefix=f"/genres", tags=["genres"])
app.include_router(stars_router, prefix=f"/stars", tags=["stars"])


def authenticate_docs(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "Password12345@")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access to API docs",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/docs", include_in_schema=False)
async def get_swagger(username: str = Depends(authenticate_docs)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Docs")

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api(username: str = Depends(authenticate_docs)):
    return get_openapi(title=app.title, version=app.version, routes=app.routes)
