from pydantic import BaseModel, ConfigDict


class UserPostIn(BaseModel):
    body: str


class UserPost(UserPostIn):
    id: int
    user_id: int
    image_url: str | None = None

    # NOTE: to return SQLAlchemy row object at endpoint (== orm_mode = True)
    model_config = ConfigDict(from_attributes=True)


class UserPostWithLikes(UserPost):
    likes: int

    model_config = ConfigDict(from_attributes=True)


class CommentIn(BaseModel):
    body: str
    post_id: int


class Comment(CommentIn):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class UserPostWithComments(BaseModel):
    post: UserPostWithLikes  # specific post를 request 할 때만 사용하므로 변경
    comments: list[Comment]


class PostLikeIn(BaseModel):
    post_id: int


class PostLike(PostLikeIn):
    id: int
    user_id: int
