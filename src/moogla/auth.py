from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Simple user model with a unique username."""

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, sa_column_kwargs={"unique": True})
    hashed_password: str
