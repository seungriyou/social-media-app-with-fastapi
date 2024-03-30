import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from socialapi.database import database
from socialapi.logging_conf import configure_logging
from socialapi.routers.post import router as post_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Hello World")

    await database.connect()  # startup: setup
    yield  # -- pause execution until sth happens(= FastAPI tells it to continue) -- #
    await database.disconnect()  # shutdown: teardown (when FastAPI app terminates)


app = FastAPI(lifespan=lifespan)

app.include_router(post_router)
