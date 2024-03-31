import os
from typing import AsyncGenerator, Generator  # fixture의 type hint

import pytest  # 어떤 function이 fixture를 정의하는지 알리기 위해
from fastapi.testclient import TestClient

# FastAPI server를 시작하지 않고서도 test 가능
from httpx import ASGITransport, AsyncClient  # API로 request를 보내는 역할

# overwrite ENV_STATUS = "test" before importing modules
os.environ["ENV_STATE"] = "test"

from socialapi.database import metadata  # noqa: E402
from socialapi.database import database, engine, user_table  # noqa: E402
from socialapi.main import app  # noqa: E402

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
    await database.connect()  # at the beginning of test function, connect to database
    yield  # run test function (pause this fixture)
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
async def logged_in_token(async_client: AsyncClient, registered_user: dict) -> str:
    # registered_user includes user id, but pydantic strips away if doesn't need it
    response = await async_client.post("/token", json=registered_user)
    return response.json()["access_token"]
