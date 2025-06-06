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
    username: Optional[str] = None
    firstname: Optional[str] = None
    middlename: Optional[str] = None
    lastname: Optional[str] = None
    profile_picture: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class UserProfileRequest(BaseModel):
    github_username: Optional[str] = None
    bio : Optional[str] = None
    profession: Optional[str] = None
    job_title: Optional[str] = None
    years_of_experience: Optional[int] = None
    website_url: Optional[str] = None
    location: Optional[str] = None
    open_to_work: Optional[bool] = None
    availability: Optional[str] = None
    profile_picture: Optional[str] = None


class UserSettingsUpdateRequest(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None
    primary_theme: Optional[str] = None
    secondary_theme: Optional[str] = None
    layout_style: Optional[str] = None

