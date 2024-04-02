import httpx
import pytest
from databases import Database
from fastapi import status

from socialapi.database import post_table
from socialapi.tasks import (
    APIResponseError,
    _generate_cute_creature_api,
    generate_and_add_to_post,
    send_simple_email,
)


# ----- email ----- #
@pytest.mark.anyio
async def test_send_simple_email(mock_httpx_client):
    await send_simple_email("test@example.net", "Test Subject", "Test Body")
    # check if post method of mock_httpx_client is called
    mock_httpx_client.post.assert_called()


@pytest.mark.anyio
async def test_send_simple_email_api_error(mock_httpx_client):
    # override the return value of the httpx client's post method (to error)
    mock_httpx_client.post.return_value = httpx.Response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content="",
        request=httpx.Request("POST", "//"),
    )

    with pytest.raises(APIResponseError):
        await send_simple_email("test@example.net", "Test Subject", "Test Body")


# ----- DeepAI image generator ----- #
@pytest.mark.anyio
async def test_generate_cute_creature_api_success(mock_httpx_client):
    # API 결과 setting
    json_data = {"output_url": "https://example.com/image.jpg"}

    mock_httpx_client.post.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        json=json_data,
        request=httpx.Request("POST", "//"),
    )

    result = await _generate_cute_creature_api("A cat")

    assert result == json_data


@pytest.mark.anyio
async def test_generate_cute_creature_api_server_error(mock_httpx_client):
    mock_httpx_client.post.return_value = httpx.Response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content="",
        request=httpx.Request("POST", "//"),
    )

    with pytest.raises(
        APIResponseError, match="API request failed with status code 500"
    ):
        await _generate_cute_creature_api("A cat")


@pytest.mark.anyio
async def test_generate_cute_creature_api_json_error(mock_httpx_client):
    mock_httpx_client.post.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        content="Not JSON",
        request=httpx.Request("POST", "//"),
    )

    with pytest.raises(APIResponseError, match="API response parsing failed"):
        await _generate_cute_creature_api("A cat")


# database
@pytest.mark.anyio
async def test_generate_and_add_to_post_success(
    mock_httpx_client, created_post: dict, confirmed_user: dict, db: Database
):
    # API 결과 setting
    json_data = {"output_url": "https://example.com/image.jpg"}

    mock_httpx_client.post.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        json=json_data,
        request=httpx.Request("POST", "//"),
    )

    # post에 generate 한 결과 add
    await generate_and_add_to_post(
        confirmed_user["email"], created_post["id"], "/post/1", db, "A cat"
    )

    # db 확인
    query = post_table.select().where(post_table.c.id == created_post["id"])
    updated_post = await db.fetch_one(
        query
    )  #  when select, db.fetch_all() / db.fecth_one()
    assert updated_post.image_url == json_data["output_url"]
