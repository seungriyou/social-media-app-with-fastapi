import httpx
import pytest
from fastapi import status

from socialapi.tasks import APIResponseError, send_simple_email


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
