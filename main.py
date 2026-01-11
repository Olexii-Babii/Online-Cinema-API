from fastapi import FastAPI
from routes.accounts import router as accounts_router
app = FastAPI()

app.include_router(accounts_router, prefix=f"/accounts", tags=["accounts"])