from httpx import AsyncClient


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
