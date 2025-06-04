from pydantic import BaseModel, EmailStr
from uuid import UUID  # For proper UUID validation
from typing import Optional


class UserBase(BaseModel):
    id: UUID | None = None  # Optional UUID for user ID
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserSettingsBase(BaseModel):
    language: str | None = None
    theme: str | None = None
    primaryTheme: str | None = None


class UserSettings(UserSettingsBase):
    id: int
    owner_id: UUID  # Use UUID for owner_id to match User model

    class Config:
        from_attributes = True


class DBUser(UserBase):
    is_active: bool
    role: str | None = None
    settings: Optional[UserSettings] = None  # Optional relationship to UserSettings
    hashed_password: str  # 

    class Config:
        from_attributes = True  # For Pydantic v2 (was `orm_mode` in v1)


class UserSettingsCreate(UserSettingsBase):
    pass
