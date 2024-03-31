import datetime
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from socialapi.config import config
from socialapi.database import database, user_table

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"])

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

# set tokenURL as the endpoint that a user can send their email(= username) and password to get a token back
# (1) helps to build automated documentation
# (2) lets us very easily grab the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# for easy testing
def access_token_expire_minutes() -> int:
    return 30


def create_access_token(email: str) -> str:
    logger.debug("Creating access token", extra={"email": email})
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=access_token_expire_minutes()
    )

    jwt_data = {"sub": email, "exp": expire}
    encoded_jwt = jwt.encode(
        jwt_data, key=config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM
    )

    return encoded_jwt


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # NOTE: 같은 password를 두 번 hash 하더라도, 그 값은 다르다! 따라서 verfy() 메서드를 이용한다.
    return pwd_context.verify(plain_password, hashed_password)


async def get_user(email: str):
    logger.debug("Fetching user from the database", extra={"email": email})
    query = user_table.select().where(user_table.c.email == email)

    result = await database.fetch_one(query)
    if result:
        return result


async def authenticate_user(email: str, password: str):
    logger.debug("Authenticating user", extra={"email": email})

    # 1. DB에서 email이 일치하는 사용자 찾기
    user = await get_user(email)

    # 2. 일치하는 사용자가 없으면 exception
    if not user:
        raise credentials_exception

    # 3. password가 일치하지 않으면 exception
    if not verify_password(password, user.password):
        raise credentials_exception

    # 4. 찾은 사용자 반환
    return user


# dependency injection -> no need to call oauth2_scheme
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        # decode token
        payload = jwt.decode(
            token, key=config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
        )
        # get email from token
        email = payload.get("sub")
        if email is None:
            raise credentials_exception

    # if token is expired
    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # if authentication failed
    except JWTError as e:
        raise credentials_exception from e

    # get user with email from database
    user = await get_user(email=email)
    if user is None:
        raise credentials_exception

    return user
