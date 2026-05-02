from decouple import config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.account.routers import router as account_router

app = FastAPI(
    title="FastAPI E-Commerce Backend",
    description="A simple FastAPI E-Commerce application",
    version="1.0.0",
)


app.mount("/media", StaticFiles(directory="media"), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Welcome to the E-Commerce API"}


app.include_router(account_router, prefix="/api/account", tags=["Account"])
