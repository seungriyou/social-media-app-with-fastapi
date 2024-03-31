import logging

from fastapi import APIRouter, HTTPException, status

from socialapi.database import database, user_table
from socialapi.models.user import UserIn
from socialapi.security import get_password_hash, get_user

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
