import os
from typing import AsyncGenerator, Generator  # fixture의 type hint
from unittest.mock import AsyncMock, Mock

import pytest  # 어떤 function이 fixture를 정의하는지 알리기 위해
from fastapi import status
from fastapi.testclient import TestClient

# FastAPI server를 시작하지 않고서도 test 가능
from httpx import Request  # API로 request를 보내는 역할
from httpx import ASGITransport, AsyncClient, Response

# overwrite ENV_STATUS = "test" before importing modules
os.environ["ENV_STATE"] = "test"

from socialapi.database import metadata  # noqa: E402
from socialapi.database import database, engine, user_table  # noqa: E402
from socialapi.main import app  # noqa: E402
from socialapi.tests.helpers import create_post  # noqa: E402

# NOTE: fixtures = ways to share data between multiple tests

# NOTE: table 구조를 바꿀 때마다 test.db를 삭제해야 한다!
metadata.create_all(engine)


@pytest.fixture(scope="session")  # runs only once for the entire test session
def anyio_backend():
    # fastapi에서 async function을 사용하려면 async platform이 필요하며,
    # fastapi에게 built in asyncio framework를 async test를 실행할 때 사용하라고 알려줌
    return "asyncio"


@pytest.fixture()
def client() -> Generator:
    yield TestClient(app)  # yield를 사용하면 이전/이후에 동작 추가 가능


@pytest.fixture(autouse=True)  # runs at every test (test parameter로 안 넣어도 됨)
async def db() -> AsyncGenerator:  # 추후 DB로 바꿀 것이므로 async
    """
    `test_tasks.py`의 `test_generate_and_add_to_post_success`
    -> db를 받아서 사용할 것이므로, yield database 해야 한다!
    """
    await database.connect()  # at the beginning of test function, connect to database
    yield database  # run test function (pause this fixture)
    await database.disconnect()  # disconnect from db and rollback


# httpx를 이용하여 API에게 request를 보내는 역할 (test parameter로 넣기)
@pytest.fixture()
async def async_client(client) -> AsyncGenerator:
    # 위에서 선언한 fixture인 `client`를 자동으로 파라미터로 주입 받게 됨 (= dependency injection)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=client.base_url
    ) as ac:
        yield ac


@pytest.fixture()
async def registered_user(async_client: AsyncClient) -> dict:
    # register user
    user_details = {"email": "test@example.net", "password": "1234"}
    await async_client.post("/register", json=user_details)

    # fetch the information we created & add id
    query = user_table.select().where(user_table.c.email == user_details["email"])
    user = await database.fetch_one(query)
    user_details["id"] = user.id

    return user_details


@pytest.fixture()
async def confirmed_user(registered_user: dict) -> dict:
    query = (
        user_table.update()
        .where(user_table.c.email == registered_user["email"])
        .values(confirmed=True)
    )
    await database.execute(query)
    return registered_user


@pytest.fixture()
async def logged_in_token(async_client: AsyncClient, confirmed_user: dict) -> str:
    # registered_user includes user id, but pydantic strips away if doesn't need it
    response = await async_client.post(
        "/token",
        data={
            "username": confirmed_user["email"],
            "password": confirmed_user["password"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return response.json()["access_token"]


@pytest.fixture(autouse=True)
def mock_httpx_client(mocker):
    """test 시에는 mailgun으로 post request 보내는 동작이 실행되지 않도록 한다."""

    # `socialapi.tasks.httpx.AsyncClient`를 통해 request를 보낼 때마다, 실제로 API를 호출하지 않고 200 return 하도록 한다.
    mocked_client = mocker.patch("socialapi.tasks.httpx.AsyncClient")

    mocked_async_client = Mock()
    # NOTE: response는 200, 빈 content로 설정하고, 받은 request는 home URL(//)로부터 POST로 보내졌다고 설정한다.
    response = Response(
        status_code=status.HTTP_200_OK, content="", request=Request("POST", "//")
    )
    mocked_async_client.post = AsyncMock(return_value=response)
    mocked_client.return_value.__aenter__.return_value = mocked_async_client

    # for the case we need to use it somewhere
    return mocked_async_client


@pytest.fixture()
async def created_post(async_client: AsyncClient, logged_in_token: str):
    # fixture는 dependency injection 지원 (async_client가 injected dynamically)
    # async_client를 타고타고 올라가서 최종적으로 tests/conftest.py에서 찾게됨
    """
    [ `created_post`를 `autouse=True` 하지 않는 이유 ]
        - test에서 인자로 `created_post`를 받게 되는데, 이렇게 하면 그 test는 이미 생성된 post를 가지고 동작하며, response에 접근할 수 있음
        - 즉, test가 실행될 때 post가 이미 생성되어 존재해야 하기 때문
        - naming convention을 통해 test의 가독성을 좋게함
    """
    return await create_post("Test Post", async_client, logged_in_token)
