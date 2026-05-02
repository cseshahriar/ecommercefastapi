from typing  import AsyncGenerator, Annotated

from fastapi import Depends
from decouple import config
from sqlalchemy import future
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker ,create_async_engine


# Read configuration from .env file or environment variables
DB_USER = config("DB_USER")
DB_PASS = config("DB_PASS")
DB_NAME = config("DB_NAME")
DB_PORT = config("DB_PORT")
DB_HOST = config("DB_HOST")


DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL, echo=True, future=True)  # echo for dev terminal info show
async_session = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
