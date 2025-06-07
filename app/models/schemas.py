from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


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
    username: Optional[str] = None
    firstname: Optional[str] = None
    middlename: Optional[str] = None
    lastname: Optional[str] = None
    profile_picture: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True


class UserProfileRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None
    github_username: Optional[str] = None
    bio: Optional[str] = None
    profession: Optional[str] = None
    job_title: Optional[str] = None
    years_of_experience: Optional[int] = None
    website_url: Optional[str] = None
    location: Optional[str] = None
    open_to_work: Optional[bool] = None
    availability: Optional[str] = None
    profile_picture: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)  # For Pydantic v2


class UserSettingsUpdateRequest(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None
    primary_theme: Optional[str] = None
    secondary_theme: Optional[str] = None
    layout_style: Optional[str] = None


class UserDevicesRequest(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[str] = None  # e.g., 'mobile', 'desktop', 'tablet'
    last_used: Optional[datetime] = None  # ISO format date string
    user_id: Optional[uuid.UUID] = None  # User ID to associate with the device
