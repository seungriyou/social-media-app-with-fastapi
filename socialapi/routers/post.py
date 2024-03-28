from fastapi import APIRouter, HTTPException, status

from socialapi.models.post import (
    Comment,
    CommentIn,
    UserPost,
    UserPostIn,
    UserPostWithComments,
)

# model: to validate data (that client sends us)

router = APIRouter()
post_table = {}
comment_table = {}


def find_post(post_id: int):
    return post_table.get(post_id)


@router.post("/post", response_model=UserPost, status_code=status.HTTP_201_CREATED)
async def create_post(post: UserPostIn):
    data = post.model_dump()
    last_recored_id = len(post_table)
    new_post = {**data, "id": last_recored_id}
    post_table[last_recored_id] = new_post
    return new_post


@router.get("/post", response_model=list[UserPost])
async def get_all_posts():
    """
    Pydantic이 list[UserPost]를 JSON으로 변환해서 response로 전달
    """
    return list(post_table.values())


@router.post("/comment", response_model=Comment, status_code=status.HTTP_201_CREATED)
async def create_comment(comment: CommentIn):
    post = find_post(comment.post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    data = comment.model_dump()
    last_recored_id = len(comment_table)
    new_comment = {**data, "id": last_recored_id}
    comment_table[last_recored_id] = new_comment
    return new_comment


@router.get("/post/{post_id}/comment", response_model=list[Comment])
async def get_comments_on_post(post_id: int):
    return [
        comment for comment in comment_table.values() if comment["post_id"] == post_id
    ]


@router.get("/post/{post_id}", response_model=UserPostWithComments)
async def get_post_with_comments(post_id: int):
    post = find_post(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    return {
        "post": post,
        "comments": await get_comments_on_post(post_id),
    }
