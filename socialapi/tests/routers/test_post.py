import pytest
from fastapi import status
from httpx import AsyncClient

from socialapi import security
from socialapi.tests.helpers import create_comment, create_post, like_post


# ===== fixtures ===== #
# NOTE: fixtures should be at the highest level possible in the hierarchy
@pytest.fixture()
async def created_comment(
    async_client: AsyncClient, created_post: dict, logged_in_token: str
):
    return await create_comment(
        "Test Post", created_post["id"], async_client, logged_in_token
    )


@pytest.fixture()
def mock_generate_cute_creature_api(mocker):
    return mocker.patch(
        "socialapi.tasks._generate_cute_creature_api",
        return_value={"output_url": "http://example.net/image.jpg"},
    )


# ===== tests ===== #
# ----- post ----- #
@pytest.mark.anyio  # test마다 우리가 설정한 async platform을 사용하도록 알려야 함 (여기에서는 anyio 사용)
async def test_create_post(
    async_client: AsyncClient, confirmed_user: dict, logged_in_token: str
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
        "user_id": confirmed_user["id"],
        "image_url": None,
    }.items() <= response.json().items()


@pytest.mark.anyio
async def test_create_post_with_prompt(
    async_client: AsyncClient, logged_in_token: str, mock_generate_cute_creature_api
):
    body = "Test Post"

    response = await async_client.post(
        "/post?prompt=A cat",  # -- w/ query parameter
        json={"body": body},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert {
        "id": 1,
        "body": body,
        "image_url": None,  # -- should be None
    }.items() <= response.json().items()
    mock_generate_cute_creature_api.assert_called()  # -- ensure third party API was going to be called


@pytest.mark.anyio
async def test_create_post_expired_token(
    async_client: AsyncClient, confirmed_user: dict, mocker
):
    mocker.patch("socialapi.security.access_token_expire_minutes", return_value=-1)
    token = security.create_access_token(confirmed_user["email"])
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
    confirmed_user: dict,
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
        "user_id": confirmed_user["id"],
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
