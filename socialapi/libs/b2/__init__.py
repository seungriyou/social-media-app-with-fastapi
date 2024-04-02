import logging
from functools import lru_cache

import b2sdk.v2 as b2

from socialapi.config import config

logger = logging.getLogger(__name__)

# NOTE: third party APIs와 상호작용 할 때는 logging을 꼭 하자! 어디서 문제가 발생했는지 알기 위해서..


@lru_cache()
def b2_api():
    logger.debug("Creating and authorizing B2 API")

    # NOTE: auth 정보가 바뀌지 않을 것이므로 lru_cache()
    info = b2.InMemoryAccountInfo()
    b2_api = b2.B2API(info)

    b2_api.authorize_account("production", config.B2_KEY_ID, config.B2_APPLICATION_KEY)
    return b2_api


@lru_cache()
def b2_get_bucket(api: b2.B2Api):
    # NOTE: bucket을 하나만 사용할 것이므로 lru_cache()
    return api.get_bucket_by_name(config.B2_BUCKET_NAME)


def b2_upload_file(local_file: str, file_name: str) -> str:
    # NOTE: b2_api()는 첫 호출 시에만 계산되고, 그 후로는 cached value가 반환된다.
    api = b2_api()

    logger.debug(f"Uploading {local_file} to B2 as {file_name}")

    uploaded_file = b2_get_bucket(api).upload_local_file(
        local_file=local_file, file_name=file_name
    )

    # NOTE: public bucket에 file을 올리면, download url을 얻을 수 있다.
    download_url = api.get_download_url_for_fileid(uploaded_file.id_)
    logger.debug(
        f"Uploaded {local_file} to B2 successfully and got download URL {download_url}"
    )

    return download_url
