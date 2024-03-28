from typing import AsyncGenerator, Generator  # fixture의 type hint

import pytest  # 어떤 function이 fixture를 정의하는지 알리기 위해
from fastapi.testclient import TestClient

# FastAPI server를 시작하지 않고서도 test 가능
from httpx import ASGITransport, AsyncClient  # API로 request를 보내는 역할

from socialapi.main import app
from socialapi.routers.post import comment_table, post_table

# fixtures: ways to share data between multiple tests


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
    post_table.clear()
    comment_table.clear()
    yield


# httpx를 이용하여 API에게 request를 보내는 역할 (test parameter로 넣기)
@pytest.fixture()
async def async_client(client) -> AsyncGenerator:
    # 위에서 선언한 fixture인 `client`를 자동으로 파라미터로 주입 받게 됨 (= dependency injection)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=client.base_url
    ) as ac:
        yield ac
