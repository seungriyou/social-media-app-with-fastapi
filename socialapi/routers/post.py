import logging

from fastapi import APIRouter, HTTPException, status

from socialapi.database import comment_table, database, post_table
from socialapi.models.post import (
    Comment,
    CommentIn,
    UserPost,
    UserPostIn,
    UserPostWithComments,
)

# NOTE: model = to validate data (that client sends us)

router = APIRouter()

logger = logging.getLogger(__name__)  # socialapi.routers.post


async def find_post(post_id: int):
    logger.info(f"Finding post with id {post_id}")

    query = post_table.select().where(post_table.c.id == post_id)

    logger.debug(query)

    return await database.fetch_one(query)


@router.post("/post", response_model=UserPost, status_code=status.HTTP_201_CREATED)
async def create_post(post: UserPostIn):
    logger.info("Creating post")

    data = post.model_dump()
    query = post_table.insert().values(data)

    logger.debug(query)

    last_record_id = await database.execute(query)  # returns generated id
    # NOTE: it's okay to return dict, because Pydantic knows how to deal with it
    return {**data, "id": last_record_id}


@router.get("/post", response_model=list[UserPost])
async def get_all_posts():
    logger.info("Getting all posts")

    # Pydantic이 list[UserPost]를 JSON으로 변환해서 response로 전달
    query = post_table.select()

    logger.debug(query)

    return await database.fetch_all(query)


@router.post("/comment", response_model=Comment, status_code=status.HTTP_201_CREATED)
async def create_comment(comment: CommentIn):
    logger.info("Creating comment")

    post = await find_post(
        comment.post_id
    )  # await -> finishes running before we continue
    if not post:
        logger.error(f"Post with id {comment.post_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    data = comment.model_dump()
    query = comment_table.insert().values(data)
    last_record_id = await database.execute(query)
    return {**data, "id": last_record_id}


@router.get("/post/{post_id}/comment", response_model=list[Comment])
async def get_comments_on_post(post_id: int):
    logger.info("Getting comments on post")

    # NOTE: filtering by key(primary / foreign) is much faster in SQLAlchemy
    query = comment_table.select().where(comment_table.c.post_id == post_id)

    logger.debug(query)

    return await database.fetch_all(query)


@router.get("/post/{post_id}", response_model=UserPostWithComments)
async def get_post_with_comments(post_id: int):
    logger.info("Getting post and its comments")

    post = await find_post(post_id)
    if not post:
        logger.error(f"Post with post id {post_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    return {
        "post": post,
        "comments": await get_comments_on_post(post_id),
    }
