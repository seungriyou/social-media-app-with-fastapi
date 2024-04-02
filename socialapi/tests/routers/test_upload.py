# NOTE: third party library가 제대로 동작하는지 확인할 필요가 없다!
# (1) Backblaze B2 bucket에 아무것도 올리지 않도록 해야 한다.
# (2) test 시에는 실제 파일을 생성하면 안 된다.

import contextlib
import os
import pathlib
import tempfile

import pytest
from fastapi import status
from httpx import AsyncClient


# NOTE: fs fixture: pyfakefs gives
@pytest.fixture()
def sample_image(fs) -> pathlib.Path:
    path = (pathlib.Path(__file__).parent / "assets" / "myfile.png").resolve()
    fs.create_file(path)
    return path


@pytest.fixture(autouse=True)
def mock_b2_upload_file(mocker):
    return mocker.patch(
        # NOTE: routers/upload.py에서 import 된 b2_upload_file을 mock (target very specifically)
        "socialapi.routers.upload.b2_upload_file",
        return_value="https://fakeurl.com",
    )


# NOTE: routers/upload.py에서 aiofiles.open() 시에 fake file system을 읽도록 해야 한다.
"""
- 일반적인 open()을 사용한다면, pyfakefs가 이미 open function을 patch 하므로 자동으로 fake file system으로부터 읽는다.
- 하지만, aiofiles.open()을 사용한다면, 실제 file system으로부터 읽지 않도록 우리가 직접 patch 해야 한다!
    - aiofiles.open()이 아닌, 일반 open()을 사용하도록 해야 한다.
    - 따라서 asynchronous 하게 동작하지 않고 synchronous 하게 동작한다. (이것에 대해서는 테스트 할 필요 없으므로!)
"""


@pytest.fixture(autouse=True)
def aiofiles_mock_open(mocker, fs):
    mock_open = mocker.patch("aiofiles.open")

    # NOTE: aiofiles가 fake file system을 사용하도록 한다.
    @contextlib.asynccontextmanager
    async def async_file_open(fname: str, mode: str = "r"):
        # out_fs_mock: aiofiles.open()이 return 하는 f를 대체
        out_fs_mock = mocker.AsyncMock(name=f"async_file_open:{fname!r}/{mode!r}")

        # aiofiles.open()이 return 하는 f의 read & write 동작을 open()의 read & write 동작으로 바꾸기
        # NOTE: open()의 read & write는 이미 pyfakefs로 인해 patched 되어 있다!
        with open(fname, mode) as fin:
            out_fs_mock.read.side_effect = fin.read
            out_fs_mock.write.side_effect = fin.write
            yield out_fs_mock

    mock_open.side_effect = async_file_open
    return mock_open


async def call_upload_endpoint(
    async_client: AsyncClient, token: str, sample_image: pathlib.Path
):
    return await async_client.post(
        "/upload",
        files={"file": open(sample_image, "rb")},
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.mark.anyio
async def test_upload_image(
    async_client: AsyncClient, logged_in_token: str, sample_image: pathlib.Path
):
    response = await call_upload_endpoint(async_client, logged_in_token, sample_image)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["file_url"] == "https://fakeurl.com"


# TODO: what is the difference between spy and mocker
@pytest.mark.anyio
async def test_temp_file_removed_after_upload(
    async_client: AsyncClient, logged_in_token: str, sample_image: pathlib.Path, mocker
):
    named_temp_file_spy = mocker.spy(tempfile, "NamedTemporaryFile")

    response = await call_upload_endpoint(async_client, logged_in_token, sample_image)
    assert response.status_code == status.HTTP_201_CREATED

    created_temp_file = named_temp_file_spy.spy_return
    assert not os.path.exists(created_temp_file.name)
