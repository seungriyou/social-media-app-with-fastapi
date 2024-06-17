import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from socialapi import tasks
from socialapi.database import database, user_table
from socialapi.models.user import UserIn
from socialapi.security import (
    authenticate_user,
    create_access_token,
    create_confirmation_token,
    get_password_hash,
    get_subject_for_token_type,
    get_user,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# NOTE: BackgroundTasks: FastAPI will inject what you need into this variable (any function available)
# if the function is async, FastAPI awaits for it
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserIn, background_tasks: BackgroundTasks, request: Request):
    if await get_user(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exists",
        )

    # NOTE: MUST save password after hashing
    hashed_password = get_password_hash(user.password)
    query = user_table.insert().values(email=user.email, password=hashed_password)

    logger.debug(query)

    await database.execute(query)

    # send email confirmation (modify: await -> background task)
    background_tasks.add_task(
        tasks.send_user_registration_email,  # -- just passing the function (followings are arguments)
        email=user.email,
        # NOTE: request.url_for(): generate a URL for a particular endpoint
        confirmation_url=request.url_for(
            "confirm_email", token=create_confirmation_token(user.email)
        ),
    )

    return {"detail": "User created. Please confirm your email"}


@router.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # 1. 사용자 인증 (사용자 존재하는지, password 일치하는지) 등
    user = await authenticate_user(form_data.username, form_data.password)

    # 2. access token 생성
    access_token = create_access_token(user.email)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirm/{token}")
async def confirm_email(token: str):
    email = get_subject_for_token_type(token, "confirmation")
    query = (
        user_table.update().where(user_table.c.email == email).values(confirmed=True)
    )

    logger.debug(query)

    await database.execute(query)
    return {"detail": "User confirmed"}
