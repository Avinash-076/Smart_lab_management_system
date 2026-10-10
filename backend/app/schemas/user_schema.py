from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    full_name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=100)
    role_id: int = Field(gt=0)
    is_active: bool = True


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    role_id: int = Field(gt=0)
    full_name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role_id: int | None = Field(default=None, gt=0)
    full_name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=100)
    is_active: bool | None = Field(default=None)


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    email: str | None = None
    role_id: int
    role_name: str | None = None
    is_active: bool = True
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    limit: int
    total_pages: int