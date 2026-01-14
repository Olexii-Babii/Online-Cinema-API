from fastapi import FastAPI

from routes.accounts import router as accounts_router
from routes.profiles import router as profiles_router

app = FastAPI()

app.include_router(accounts_router, prefix=f"/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix=f"/profiles", tags=["profiles"])
