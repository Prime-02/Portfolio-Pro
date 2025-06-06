from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserSettingsBase(BaseModel):
    language: str | None = None
    theme: str | None = None
    primary_theme: str | None = None


class UserSettings(UserSettingsBase):
    class Config:
        from_attributes = True


class DBUser(UserBase):
    is_active: bool
    role: str | None = None
    # settings: Optional[UserSettings] = None  # Optional relationship to UserSettings
    # hashed_password: str  #

    class Config:
        from_attributes = True  # For Pydantic v2 (was `orm_mode` in v1)


class UserSettingsCreate(UserSettingsBase):
    pass


class UserWithSettings(DBUser, UserSettingsBase):
    pass


class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
