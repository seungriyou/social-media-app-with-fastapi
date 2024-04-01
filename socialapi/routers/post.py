import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from socialapi.database import comment_table, database, like_table, post_table
from socialapi.models.post import (
    Comment,
    CommentIn,
    PostLike,
    PostLikeIn,
    UserPost,
    UserPostIn,
    UserPostWithComments,
)
from socialapi.models.user import User
from socialapi.security import get_current_user

# NOTE: model = to validate data (that client sends us)

router = APIRouter()

logger = logging.getLogger(__name__)  # socialapi.routers.post

"""
(1) select(post_table, func.count(like_table.c.id).label("likes"))
    => SELECT posts.id, posts.body, posts.user_id, count(likes.id) AS likes
        FROM posts, likes
(2) select(post_table, func.count(like_table.c.id).label("likes")).select_from(post_table.outerjoin(like_table))
    => SELECT posts.id, posts.body, posts.user_id, count(likes.id) AS likes 
        FROM posts LEFT OUTER JOIN likes ON posts.id = likes.post_id
(3) select(post_table, func.count(like_table.c.id).label("likes")).select_from(post_table.outerjoin(like_table)).group_by(post_table.c.id)
    => SELECT posts.id, posts.body, posts.user_id, count(likes.id) AS likes 
        FROM posts LEFT OUTER JOIN likes ON posts.id = likes.post_id
        GROUP BY posts.id
"""
"""
post_table.select().where(...) (= shortcut)
== select(post_table).select_from(post_table).where(...) (= repetitive)
"""

select_post_and_likes = (
    select(post_table, func.count(like_table.c.id).label("likes"))
    .select_from(post_table.outerjoin(like_table))
    .group_by(post_table.c.id)
)


async def find_post(post_id: int):
    logger.info(f"Finding post with id {post_id}")

    query = post_table.select().where(post_table.c.id == post_id)

    logger.debug(query)

    return await database.fetch_one(query)


@router.post("/post", response_model=UserPost, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: UserPostIn, current_user: Annotated[User, Depends(get_current_user)]
):
    # with Depends(get_current_user), following line can be removed:
    # current_user: User = await get_current_user(await oauth2_scheme(request))  # noqa

    logger.info("Creating post")

    data = {**post.model_dump(), "user_id": current_user.id}
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
async def create_comment(
    comment: CommentIn, current_user: Annotated[User, Depends(get_current_user)]
):
    logger.info("Creating comment")

    post = await find_post(
        comment.post_id
    )  # await -> finishes running before we continue
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    data = {**comment.model_dump(), "user_id": current_user.id}
    query = comment_table.insert().values(data)
    logger.debug(query)

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

    # modify -> to have "likes" column
    query = select_post_and_likes.where(post_table.c.id == post_id)

    logger.debug(query)

    post = await database.fetch_one(query)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    return {
        "post": post,
        "comments": await get_comments_on_post(post_id),
    }


@router.post("/like", response_model=PostLike, status_code=status.HTTP_201_CREATED)
async def like_post(
    like: PostLikeIn, current_user: Annotated[User, Depends(get_current_user)]
):
    logger.info("Liking post")

    post = await find_post(like.post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    data = {**like.model_dump(), "user_id": current_user.id}
    query = like_table.insert().values(data)
    logger.debug(query)

    last_record_id = await database.execute(query)
    return {**data, "id": last_record_id}
