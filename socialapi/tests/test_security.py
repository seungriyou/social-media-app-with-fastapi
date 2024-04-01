import pytest
from jose import jwt

from socialapi import security
from socialapi.config import config


def test_access_token_expire_minutes():
    assert security.access_token_expire_minutes() == 30


def test_confirm_token_expire_minutes():
    assert security.confirm_token_expire_minutes() == 1440


def test_create_access_token():
    token = security.create_access_token("123")

    assert {"sub": "123", "type": "access"}.items() <= jwt.decode(
        token, key=config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
    ).items()


def test_create_confirmation_token():
    token = security.create_confirmation_token("123")

    assert {"sub": "123", "type": "confirmation"}.items() <= jwt.decode(
        token, key=config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
    ).items()


def test_get_subject_for_token_type_valid_confirmation():
    email = "test@example.com"
    token = security.create_confirmation_token(email)

    assert email == security.get_subject_for_token_type(token, "confirmation")


def test_get_subject_for_token_type_valid_access():
    email = "test@example.com"
    token = security.create_access_token(email)

    assert email == security.get_subject_for_token_type(token, "access")


# NOTE: make test suites for every potential exception
def test_get_subject_for_token_type_expired(mocker):
    mocker.patch("socialapi.security.access_token_expire_minutes", return_value=-1)
    email = "test@example.com"
    token = security.create_access_token(email)

    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")
    assert "Token has expired" == exc_info.value.detail


def test_get_subject_for_token_type_invalid():
    token = "invalid token"

    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")
    assert "Invalid token" == exc_info.value.detail


def test_get_subject_for_token_type_missing_sub():
    # create jwt w/o sub
    email = "test@example.com"
    token = security.create_access_token(email)
    payload = jwt.decode(
        token, key=config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
    )
    del payload["sub"]
    token = jwt.encode(
        payload, key=config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM
    )

    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")
    assert "Token is missing 'sub' field" == exc_info.value.detail


def test_get_subject_for_token_type_wrong():
    email = "test@example.com"
    token = security.create_confirmation_token(email)

    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")
    assert "Token has incorrect type, expected 'access'" == exc_info.value.detail


def test_password_hashes():
    password = "password"

    assert security.verify_password(password, security.get_password_hash(password))


@pytest.mark.anyio
async def test_get_user(registered_user: dict):
    user = await security.get_user(registered_user["email"])

    assert user.email == registered_user["email"]


@pytest.mark.anyio
async def test_get_user_not_found():
    user = await security.get_user("test@example.com")

    assert user is None


@pytest.mark.anyio
async def test_authenticate_user(registered_user: dict):
    user = await security.authenticate_user(
        registered_user["email"], registered_user["password"]
    )

    assert user.email == registered_user["email"]


@pytest.mark.anyio
async def test_authenticate_user_not_found():
    # HTTPException test
    with pytest.raises(security.HTTPException):
        await security.authenticate_user("test@example.net", "1234")


@pytest.mark.anyio
async def test_authenticate_user_wrong_password(registered_user: dict):
    with pytest.raises(security.HTTPException):
        await security.authenticate_user(registered_user["email"], "wrong password")


@pytest.mark.anyio
async def test_get_current_user(registered_user: dict):
    token = security.create_access_token(registered_user["email"])
    user = await security.get_current_user(token)

    assert user.email == registered_user["email"]


@pytest.mark.anyio
async def test_get_current_user_invalid_token():
    with pytest.raises(security.HTTPException):
        await security.get_current_user("invalid token")


@pytest.mark.anyio
async def test_get_current_user_wrong_type_token(registered_user: dict):
    token = security.create_confirmation_token(registered_user["email"])

    with pytest.raises(security.HTTPException):
        await security.get_current_user(token)
