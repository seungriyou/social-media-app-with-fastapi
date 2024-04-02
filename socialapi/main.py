import logging
from contextlib import asynccontextmanager

import sentry_sdk
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler

from socialapi.config import config
from socialapi.database import database
from socialapi.logging_conf import configure_logging
from socialapi.routers.post import router as post_router
from socialapi.routers.upload import router as upload_router
from socialapi.routers.user import router as user_router

sentry_sdk.init(
    dsn=config.SENTRY_DSN,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

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
app.include_router(user_router)
app.include_router(upload_router)


@app.exception_handler(HTTPException)
async def http_exception_handle_logging(request, exc):
    logger.error(f"HTTPException: {exc.status_code} {exc.detail}")
    return await http_exception_handler(request, exc)
