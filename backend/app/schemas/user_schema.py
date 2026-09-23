from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=50,
    )

    password: str = Field(
        min_length=6,
        max_length=128,
    )

    role_id: int = Field(
        gt=0,
    )


class UserUpdate(BaseModel):
    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    password: str | None = Field(
        default=None,
        min_length=6,
        max_length=128,
    )

    role_id: int | None = Field(
        default=None,
        gt=0,
    )


class UserResponse(BaseModel):
    id: int
    username: str
    role_id: int