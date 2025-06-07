from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
import uuid
from typing import Union


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserSettingsBase(BaseModel):
    language: str | None = None
    theme: str | None = None
    primary_theme: str | None = None
    secondary_theme: str | None = None
    layout_style: str | None = None

    class Config:
        from_attributes = True


class UserSettings(UserSettingsBase):
    owner_id: uuid.UUID | None = None


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


from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
import uuid


# Professional Skills Schemas
class ProfessionalSkillsBase(BaseModel):
    skill_name: str
    proficiency_level: str  # e.g., Beginner, Intermediate, Expert
    id: uuid.UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProfessionalSkillsCreate(ProfessionalSkillsBase):
    user_id: uuid.UUID
    skill_name: Optional[str] = None
    proficiency_level: Optional[str] = None


class ProfessionalSkillsUpdate(BaseModel):
    skill_name: Optional[str] = None
    proficiency_level: Optional[str] = None


# Social Links Schemas
class SocialLinksBase(BaseModel):
    id: Optional[uuid.UUID] = None
    platform_name: str  # e.g., LinkedIn, GitHub
    profile_url: str


class SocialLinksCreate(SocialLinksBase):
    user_id: Optional[uuid.UUID] = None
    id: Optional[uuid.UUID] = None


class SocialLinksUpdate(BaseModel):
    platform_name: Optional[str] = None
    profile_url: Optional[str] = None


class SocialLinks(SocialLinksBase):
    user_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Certification Schemas
class CertificationBase(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    certification_name: str
    issuing_organization: str
    issue_date: Optional[Union[datetime, date]] = None
    expiration_date: Optional[Union[datetime, date]] = None

    model_config = ConfigDict(from_attributes=True)


class CertificationUpdate(BaseModel):
    certification_name: Optional[str] = None
    issuing_organization: Optional[str] = None
    issue_date: Optional[Union[datetime, date]] = None
    expiration_date: Optional[Union[datetime, date]] = None


# Portfolio Project Schemas
class PortfolioProjectBase(BaseModel):
    id: Optional[uuid.UUID] = None
    project_name: str
    project_description: str
    project_url: Optional[str] = None
    project_image_url: Optional[str] = None
    is_public: Optional[bool] = True


class PortfolioProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    project_url: Optional[str] = None
    project_image_url: Optional[str] = None


class PortfolioProject(PortfolioProjectBase):
    user_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CollaboratorResponse(BaseModel):
    username: str
    role: str
    can_edit: bool
    created_at: datetime
    contribution_description: Optional[str] = None  # Explicitly handles None


# Media Gallery Schemas
class MediaGalleryBase(BaseModel):
    media_type: str  # 'image', 'video', 'document', 'audio'
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    is_featured: bool = False


class MediaGalleryCreate(MediaGalleryBase):
    user_id: Optional[uuid.UUID] = None


class MediaGalleryUpdate(BaseModel):
    media_type: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    is_featured: Optional[bool] = None


class MediaGallery(MediaGalleryBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Custom Section Schemas
class CustomSectionBase(BaseModel):
    section_type: str  # 'timeline', 'gallery', 'testimonials', 'publications'
    title: str
    description: Optional[str] = None
    position: int
    is_visible: bool = True


class CustomSectionCreate(CustomSectionBase):
    user_id: Optional[uuid.UUID] = None


class CustomSectionUpdate(BaseModel):
    section_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    position: Optional[int] = None
    is_visible: Optional[bool] = None


class CustomSection(CustomSectionBase):
    id: uuid.UUID
    user_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# Custom Section Item Schemas
class CustomSectionItemBase(BaseModel):
    title: str
    subtitle: Optional[str] = None  # e.g., company for experience, degree for education
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    media_url: Optional[str] = None


class CustomSectionItemCreate(CustomSectionItemBase):
    section_id: uuid.UUID


class CustomSectionItemUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    media_url: Optional[str] = None


class CustomSectionItem(CustomSectionItemBase):
    id: uuid.UUID
    section_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# Education Schemas
class EducationBase(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: bool = False
    description: Optional[str] = None


class EducationCreate(EducationBase):
    user_id: Optional[uuid.UUID] = None


class EducationUpdate(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: Optional[bool] = None
    description: Optional[str] = None


class Education(EducationBase):
    id: uuid.UUID
    user_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# Content Block Schemas
class ContentBlockBase(BaseModel):
    block_type: str  # 'about', 'services', 'process', 'fun_facts'
    title: Optional[str] = None
    content: str
    position: int
    is_visible: bool = False


class ContentBlockCreate(ContentBlockBase):
    user_id: Optional[uuid.UUID] = None


class ContentBlockUpdate(BaseModel):
    block_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    position: Optional[int] = None
    is_visible: Optional[bool] = None


class ContentBlock(ContentBlockBase):
    id: uuid.UUID
    user_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# Testimonial Schemas
class TestimonialBase(BaseModel):
    author_name: str
    author_title: Optional[str] = None
    author_company: Optional[str] = None
    author_relationship: Optional[str] = None  # "Colleague", "Manager", "Client"
    content: str
    rating: Optional[int] = None  # 1-5 scale
    is_approved: bool = False


class TestimonialCreate(TestimonialBase):
    user_id: uuid.UUID  # Required - testimonial target user
    author_user_id: uuid.UUID  # Required - who is creating the testimonial


class TestimonialUpdate(BaseModel):
    author_name: Optional[str] = None
    author_title: Optional[str] = None
    author_company: Optional[str] = None
    author_relationship: Optional[str] = None
    content: Optional[str] = None
    rating: Optional[int] = None
    is_approved: Optional[bool] = None


class Testimonial(TestimonialBase):
    id: uuid.UUID
    user_id: uuid.UUID  # Who the testimonial is for
    author_user_id: uuid.UUID  # Who created the testimonial
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# User Project Association Schemas
class UserProjectAssociationBase(BaseModel):
    role: Optional[str] = None
    can_edit: Optional[bool] = False  # Added to match SQLAlchemy model


class UserProjectAssociationCreate(UserProjectAssociationBase):
    user_id: uuid.UUID
    project_id: uuid.UUID


class UserProjectAssociationUpdate(BaseModel):
    role: Optional[str] = None
    can_edit: Optional[bool] = None  # Optional for updates


class UserProjectAssociation(UserProjectAssociationBase):
    user_id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    project: Optional["PortfolioProject"] = (
        None  # Uncomment if PortfolioProject schema is defined
    )
    user: Optional["DBUser"] = None

    model_config = ConfigDict(from_attributes=True)


# Project Like Schemas
class ProjectLikeBase(BaseModel):
    pass


class ProjectLikeCreate(ProjectLikeBase):
    project_id: uuid.UUID
    user_id: uuid.UUID


class ProjectLike(ProjectLikeBase):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Project Comment Schemas
class ProjectCommentBase(BaseModel):
    content: str
    parent_comment_id: Optional[uuid.UUID] = None


class ProjectCommentCreate(ProjectCommentBase):
    project_id: uuid.UUID
    user_id: uuid.UUID


class ProjectCommentUpdate(BaseModel):
    content: Optional[str] = None


class ProjectComment(ProjectCommentBase):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    replies: Optional[List["ProjectComment"]] = None

    model_config = ConfigDict(from_attributes=True)


# Self-referencing model fix for ProjectComment
ProjectComment.model_rebuild()


# Project Audit Schemas
class ProjectAuditBase(BaseModel):
    action: str
    details: Optional[dict] = None  # JSON field becomes dict in Pydantic
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ProjectAuditCreate(ProjectAuditBase):
    project_id: uuid.UUID
    user_id: uuid.UUID


class ProjectAuditUpdate(BaseModel):
    action: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ProjectAudit(ProjectAuditBase):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
