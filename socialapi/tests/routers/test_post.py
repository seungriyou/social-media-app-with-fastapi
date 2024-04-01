import pytest
from fastapi import status
from httpx import AsyncClient

from socialapi import security


# ===== fixtures ===== #
async def create_post(
    body: str, async_client: AsyncClient, logged_in_token: str
) -> dict:
    # json 파라미터를 사용함으로써, json 형식으로 보내는 데에 필요한 header(ex. content type)를 자동으로 설정
    response = await async_client.post(
        "/post",
        json={"body": body},
        headers={
            "Authorization": f"Bearer {logged_in_token}"
        },  # token should be in the header
    )
    return response.json()


async def create_comment(
    body: str, post_id: int, async_client: AsyncClient, logged_in_token: str
) -> dict:
    # json 파라미터를 사용함으로써, json 형식으로 보내는 데에 필요한 header(ex. content type)를 자동으로 설정
    response = await async_client.post(
        "/comment",
        json={"body": body, "post_id": post_id},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )
    return response.json()


async def like_post(
    post_id: int, async_client: AsyncClient, logged_in_token: str
) -> dict:
    response = await async_client.post(
        "/like",
        json={"post_id": post_id},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )
    return response.json()  # for returning api response result as json


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


@pytest.fixture()
async def created_comment(
    async_client: AsyncClient, created_post: dict, logged_in_token: str
):
    return await create_comment(
        "Test Post", created_post["id"], async_client, logged_in_token
    )


# ===== tests ===== #
# ----- post ----- #
@pytest.mark.anyio  # test마다 우리가 설정한 async platform을 사용하도록 알려야 함 (여기에서는 anyio 사용)
async def test_create_post(
    async_client: AsyncClient, registered_user: dict, logged_in_token: str
):
    body = "Test Post"

    response = await async_client.post(
        "/post",
        json={"body": body},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    # 나중에 response에 다른 정보가 추가될 수 있는데, 그때마다 코드를 수정하지 않기 위해
    # ==(동일)가 아닌 <=(포함)으로 assert
    assert {
        "id": 1,
        "body": body,
        "user_id": registered_user["id"],
    }.items() <= response.json().items()


@pytest.mark.anyio
async def test_create_post_expired_token(
    async_client: AsyncClient, registered_user: dict, mocker
):
    mocker.patch("socialapi.security.access_token_expire_minutes", return_value=-1)
    token = security.create_access_token(registered_user["email"])
    response = await async_client.post(
        "/post",
        json={"body": "Test Post"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Token has expired" in response.json()["detail"]


@pytest.mark.anyio
async def test_create_post_missing_data(
    async_client: AsyncClient, logged_in_token: str
):
    response = await async_client.post(
        "/post", json={}, headers={"Authorization": f"Bearer {logged_in_token}"}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_like_post(
    async_client: AsyncClient, created_post: dict, logged_in_token: str
):
    response = await async_client.post(
        "/like",
        json={"post_id": created_post["id"]},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.anyio
async def test_get_all_posts(async_client: AsyncClient, created_post: dict):
    # post를 retrieve 해야하므로 미리 post를 생성해야 함 (created_post 이용)
    # created_post는 fixture이므로, pytest는 fixture를 찾아 inject 하며
    # 그 결과로 반환된 결과를 파라미터 created_post로 반환받음

    # 단 하나의 post만 생성되어 있을 것임 (autouse=True fixture인 db()를 통해 clear하므로)
    response = await async_client.get("/post")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{**created_post, "likes": 0}]  # add likes
    assert created_post.items() <= response.json()[0].items()  # except likes (both ok)


# ----- sorting ----- #
@pytest.mark.anyio
@pytest.mark.parametrize(
    "sorting, expected_order",
    [
        ("new", [2, 1]),
        ("old", [1, 2]),
    ],
)
async def test_get_all_posts_sorting(
    async_client: AsyncClient,
    logged_in_token: str,
    sorting: str,  # parameterize
    expected_order: list[int],  # parameterize
):
    """parameterizing in pytest"""

    # create two posts for sorting
    await create_post("Test Post 1", async_client, logged_in_token)
    await create_post("Test Post 2", async_client, logged_in_token)

    response = await async_client.get("/post", params={"sorting": sorting})
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    post_ids = [post["id"] for post in data]
    assert post_ids == expected_order


@pytest.mark.anyio
async def test_get_all_posts_sort_likes(
    async_client: AsyncClient, logged_in_token: str
):
    # create two posts for sorting
    await create_post("Test Post 1", async_client, logged_in_token)
    await create_post("Test Post 2", async_client, logged_in_token)

    # like post 1
    await like_post(1, async_client, logged_in_token)

    response = await async_client.get("/post", params={"sorting": "most_likes"})
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    post_ids = [post["id"] for post in data]
    expected_order = [1, 2]  # default value와 다른 값이 되도록 설계
    assert post_ids == expected_order


@pytest.mark.anyio
async def test_get_all_posts_wrong_sorting(async_client: AsyncClient):
    response = await async_client.get("/post", params={"sorting": "wrong"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ----- comment ----- #
@pytest.mark.anyio
async def test_create_comment(
    async_client: AsyncClient,
    created_post: dict,
    registered_user: dict,
    logged_in_token: str,
):
    body = "Test Comment"

    response = await async_client.post(
        "/comment",
        json={"body": body, "post_id": created_post["id"]},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert {
        "id": 1,
        "body": body,
        "post_id": created_post["id"],
        "user_id": registered_user["id"],
    }.items() <= response.json().items()


@pytest.mark.anyio
async def test_get_comments_on_post(
    async_client: AsyncClient, created_post: dict, created_comment: dict
):
    response = await async_client.get(f"/post/{created_post['id']}/comment")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [created_comment]


@pytest.mark.anyio
async def test_get_comments_on_post_empty(
    async_client: AsyncClient, created_post: dict
):
    response = await async_client.get(f"/post/{created_post['id']}/comment")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.anyio
async def test_get_post_with_comments(
    async_client: AsyncClient, created_post: dict, created_comment: dict
):
    response = await async_client.get(f"/post/{created_post['id']}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "post": {**created_post, "likes": 0},
        "comments": [created_comment],
    }


@pytest.mark.anyio
async def test_get_missing_post_with_comments(
    async_client: AsyncClient, created_post: dict, created_comment: dict
):
    response = await async_client.get("/post/2")  # id 2 doesn't exist

    assert response.status_code == status.HTTP_404_NOT_FOUND
