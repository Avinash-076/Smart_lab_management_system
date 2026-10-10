from pydantic import BaseModel, ConfigDict, Field


class PermissionItem(BaseModel):
    action_code: str
    allowed: bool

    model_config = ConfigDict(from_attributes=True)


class PermissionDefinition(BaseModel):
    action_code: str
    name: str
    description: str
    category: str


class RoleBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)


class RoleCreate(RoleBase):
    permissions: list[str] | None = None


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)


class RolePermissionUpdateItem(BaseModel):
    action_code: str = Field(min_length=1, max_length=50)
    allowed: bool


class RolePermissionsUpdateRequest(BaseModel):
    permissions: list[RolePermissionUpdateItem]


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    user_count: int = 0
    permissions: list[PermissionItem] = []

    model_config = ConfigDict(from_attributes=True)


class CurrentUserProfileResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    email: str | None = None
    role_id: int
    role_name: str | None = None
    is_active: bool
    permissions: list[str] = []
