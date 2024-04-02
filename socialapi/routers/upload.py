import logging
import tempfile

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, status

from socialapi.libs.b2 import b2_upload_file

logger = logging.getLogger(__name__)

router = APIRouter()

"""
[ flow ]
client (sends image) -> server (tempfile) -> B2 upload -> server (delete tempfile)

[ in order to receive a file asynchronously ]
(library: aiofiles, fastapi.UploadFile)
1. client split up file into chunks (= 1MB)
2. client sends up chunks one at a time
    - FastAPI has the async functionality to receive a chunk (UploadFile)
        -> while the chunk is uploading, it can deal with a different request
    - when client finishes sending us the other chunk, it will handle the next chunk,
      and then wait for the client to send us the following chunk
        -> while waiting, it can deal with something else
3. client sends the last chunk
    - FastAPI will finish putting all the chunks together into the temporary file
    - upload it to Backblaze B2
    - delete the temporary file
"""

CHUNK_SIZE = 1024 * 1024  # 1MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile):
    # NOTE: file is not a complete file, is a chunk!
    """
    [ UploadFile.read(CHUNK_SIZE) ]
    - in order to get the next chunk, use file.read() (-> async method of the UploadFile class)
    - when data finally all reaches our server the whole 1MB, then
        - this will handle that chunk or
        - it will read it and give us a variable that we can store in a file
    """
    try:
        with tempfile.NamedTemporaryFile() as temp_file:
            filename = temp_file.name
            logger.info(f"Saving uploaded file temporarily to {filename}")

            async with aiofiles.open(filename, "wb") as f:
                """
                same as
                ```
                chunk = await file.read(CHUNK_SIZE)
                while chunk:
                    await f.write(chunk)
                    chunk = await file.read(CHUNK_SIZE)
                ```
                """
                # chunks가 async fashion으로 read 된다는 것은, read 하는 동안은 다른 일 가능하다는 것
                # while loop는 chunks를 모두 읽고 write 완료하면 exit
                # -> 즉, Backblaze B2에 upload 될 준비 완료!
                while chunk := await file.read(CHUNK_SIZE):
                    await f.write(chunk)

                # filename = tempfile 이름(random string) / file.filename = 실제 file 이름
                file_url = b2_upload_file(local_file=filename, file_name=file.filename)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error uploading the file",
        )

    # NOTE: user profile image upload에 사용한다면, file_url을 DB에 User's model profile image URL로 저장하면 된다!
    return {"detail": f"Successfully uploaded {file.filename}", "file_url": file_url}
