import logging

from fastapi import APIRouter, HTTPException, status

from socialapi.database import database, user_table
from socialapi.models.user import UserIn
from socialapi.security import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_user,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserIn):
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

    return {"detail": "User created"}


@router.post("/token")
async def login(user: UserIn):
    # 1. 사용자 인증 (사용자 존재하는지, password 일치하는지) 등
    user = await authenticate_user(user.email, user.password)

    # 2. access token 생성
    access_token = create_access_token(user.email)

    return {"access_token": access_token, "token_type": "bearer"}
