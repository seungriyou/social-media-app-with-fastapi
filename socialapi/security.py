import datetime
import logging
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from socialapi.config import config
from socialapi.database import database, user_table

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"])


def create_credentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# set tokenURL as the endpoint that a user can send their email(= username) and password to get a token back
# (1) helps to build automated documentation
# (2) lets us very easily grab the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# for easy testing
def access_token_expire_minutes() -> int:
    return 30


def confirm_token_expire_minutes() -> int:
    return 1440  # 24 hours


def create_access_token(email: str) -> str:
    logger.debug("Creating access token", extra={"email": email})
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=access_token_expire_minutes()
    )

    jwt_data = {"sub": email, "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(
        jwt_data, key=config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM
    )

    return encoded_jwt


def create_confirmation_token(email: str) -> str:
    logger.debug("Creating confirmation token", extra={"email": email})
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=confirm_token_expire_minutes()
    )

    jwt_data = {"sub": email, "exp": expire, "type": "confirmation"}
    encoded_jwt = jwt.encode(
        jwt_data, key=config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM
    )

    return encoded_jwt


def get_subject_for_token_type(
    token: str, type: Literal["access", "confirmation"]
) -> str:
    # NOTE: with `Literal`, that value should be either options
    """
    [ Improvements ]
    1. try 문에는 exception 발생 가능한 코드만 넣기
    2. type parameter의 경우, 가능한 경우를 한정하기 위해 Literal 넣기
    3. 기존의 credentials_exception 세분화
    """

    try:
        # NOTE: include the code that might raise error only! (better practice)
        # decode token
        payload = jwt.decode(
            token, key=config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
        )
    # if token is expired
    except ExpiredSignatureError as e:
        raise create_credentials_exception("Token has expired") from e
    # if authentication failed
    except JWTError as e:
        raise create_credentials_exception("Invalid token") from e

    # get email from token
    email = payload.get("sub")
    if email is None:
        raise create_credentials_exception("Token is missing 'sub' field")

    # check if the type is "access" ("confirmation" token shouldn't be accepted)
    token_type = payload.get("type")
    if token_type is None or token_type != type:
        raise create_credentials_exception(
            f"Token has incorrect type, expected '{type}'"
        )

    return email


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

    # NOTE: email / password 중 무엇이 틀렸는지 정확히 알려주면 안 된다. (potential attacker)
    # 2. 일치하는 사용자가 없으면 exception
    if not user:
        raise create_credentials_exception("Invalid email or password")

    # 3. password가 일치하지 않으면 exception
    if not verify_password(password, user.password):
        raise create_credentials_exception("Invalid email or password")

    # 4. 사용자가 confirmed 되지 않은 사용자라면
    if not user.confirmed:
        raise create_credentials_exception("User has not confirmed email")

    # 5. 찾은 사용자 반환
    return user


# dependency injection -> no need to call oauth2_scheme
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    email = get_subject_for_token_type(token, "access")

    # get user with email from database
    user = await get_user(email=email)
    if user is None:
        raise create_credentials_exception("Could not find user for this token")

    return user
