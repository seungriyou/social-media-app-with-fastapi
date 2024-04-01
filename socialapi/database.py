import databases
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)

from socialapi.config import config

# NOTE: Python에서는 module이 import 될 때 해당 코드가 실행됨 -> config가 생성됨

# <1> metadata object stores information of tables and columns -> can validate relationships
metadata = MetaData()

# <2> define tables
post_table = Table(
    "posts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("body", String),
    Column("user_id", ForeignKey("users.id"), nullable=False),
)

comment_table = Table(
    "comments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("body", String),
    Column("post_id", ForeignKey("posts.id"), nullable=False),
    Column("user_id", ForeignKey("users.id"), nullable=False),
)

user_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String, unique=True),
    Column("password", String),
)

like_table = Table(
    "likes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("post_id", ForeignKey("posts.id"), nullable=False),
    Column("user_id", ForeignKey("users.id"), nullable=False),
)

# <3> engine allows SQLAlchemy to connect to a specific type of database
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},  # only for sqlite
)

# <4> actually create tables (that metadata object stores) in database server
# (update) comment out for alembic migration
# metadata.create_all(engine)

# <5> get database object with which we can interact
database = databases.Database(
    config.DATABASE_URL, force_rollback=config.DB_FORCE_ROLL_BACK
)
