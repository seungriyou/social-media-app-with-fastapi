import logging
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler

from socialapi.database import database
from socialapi.logging_conf import configure_logging
from socialapi.routers.post import router as post_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    await database.connect()  # startup: setup
    yield  # -- pause execution until sth happens(= FastAPI tells it to continue) -- #
    await database.disconnect()  # shutdown: teardown (when FastAPI app terminates)


app = FastAPI(lifespan=lifespan)
# for identifying logs from the same request (correlation id)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(post_router)


@app.exception_handler(HTTPException)
async def http_exception_handle_logging(request, exc):
    logger.error(f"HTTPException: {exc.status_code} {exc.detail}")
    return await http_exception_handler(request, exc)
