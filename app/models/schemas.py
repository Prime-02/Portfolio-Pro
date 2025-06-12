from pydantic import BaseModel, EmailStr, ConfigDict, Field, Json
from typing import Optional, List, Union, Dict, Any
from datetime import datetime, date
from uuid import UUID
from enum import Enum


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserSettingsBase(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None
    primary_theme: Optional[str] = None
    secondary_theme: Optional[str] = None
    layout_style: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserSettings(UserSettingsBase):
    owner_id: Optional[UUID] = None


class DBUser(UserBase):
    id: UUID  # Added missing id field
    is_superuser: Optional[bool] = False
    is_active: bool
    role: Optional[str] = None
    created_at: Optional[datetime] = None  # Added common timestamp fields
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class UserProfileRequest(BaseModel):
    user_id: Optional[UUID] = None
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

    model_config = ConfigDict(from_attributes=True)


class UserSettingsUpdateRequest(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None
    primary_theme: Optional[str] = None
    secondary_theme: Optional[str] = None
    layout_style: Optional[str] = None


class UserDevicesRequest(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[str] = None  # e.g., 'mobile', 'desktop', 'tablet'
    last_used: Optional[datetime] = None
    user_id: Optional[UUID] = None


# Professional Skills Schemas
class ProfessionalSkillsBase(BaseModel):
    skill_name: str
    proficiency_level: str  # e.g., Beginner, Intermediate, Expert

    model_config = ConfigDict(from_attributes=True)


class ProfessionalSkillsCreate(BaseModel):
    user_id: UUID
    skill_name: str
    proficiency_level: str


class ProfessionalSkillsUpdate(BaseModel):
    skill_name: Optional[str] = None
    proficiency_level: Optional[str] = None


class ProfessionalSkills(ProfessionalSkillsBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Social Links Schemas
class SocialLinksBase(BaseModel):
    platform_name: str  # e.g., LinkedIn, GitHub
    profile_url: str

    model_config = ConfigDict(from_attributes=True)


class SocialLinksCreate(SocialLinksBase):
    user_id: UUID


class SocialLinksUpdate(BaseModel):
    platform_name: Optional[str] = None
    profile_url: Optional[str] = None


class SocialLinks(SocialLinksBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Certification Schemas
class CertificationBase(BaseModel):
    certification_name: str
    issuing_organization: str
    issue_date: Optional[Union[datetime, date]] = None
    expiration_date: Optional[Union[datetime, date]] = None

    model_config = ConfigDict(from_attributes=True)


class CertificationCreate(CertificationBase):
    user_id: UUID


class CertificationUpdate(BaseModel):
    certification_name: Optional[str] = None
    issuing_organization: Optional[str] = None
    issue_date: Optional[Union[datetime, date]] = None
    expiration_date: Optional[Union[datetime, date]] = None


class Certification(CertificationBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Media Gallery Schemas
class MediaGalleryBase(BaseModel):
    media_type: str  # 'image', 'video', 'document', 'audio'
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    is_featured: bool = False

    model_config = ConfigDict(from_attributes=True)


class MediaGalleryCreate(MediaGalleryBase):
    user_id: UUID


class MediaGalleryUpdate(BaseModel):
    media_type: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    is_featured: Optional[bool] = None


class MediaGallery(MediaGalleryBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Portfolio Project Schemas
class PortfolioProjectBase(BaseModel):
    project_name: str
    project_description: str
    project_category: Optional[str] = None
    id: Optional[UUID] = None
    project_url: Optional[str] = None
    project_image_url: Optional[str] = None
    is_public: Optional[bool] = True
    is_completed: Optional[bool] = False
    is_concept: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class PortfolioProjectCreate(PortfolioProjectBase):
    user_id: UUID


class PortfolioProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    project_category: Optional[str] = None
    project_url: Optional[str] = None
    project_image_url: Optional[str] = None
    is_public: Optional[bool] = None
    is_completed: Optional[bool] = None
    is_concept: Optional[bool] = None


class PortfolioProject(PortfolioProjectBase):
    # id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioProjectWithUsers(PortfolioProjectBase):
    users: List[DBUser] = []


# Collaborator Schemas
class CollaboratorBase(BaseModel):
    role: str
    can_edit: bool = False
    contribution_description: Optional[str] = None
    contribution: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CollaboratorCreate(CollaboratorBase):
    user_id: UUID
    portfolio_id: UUID


class CollaboratorUpdate(BaseModel):
    role: Optional[str] = None
    can_edit: Optional[bool] = None
    contribution_description: Optional[str] = None
    contribution: Optional[str] = None


class CollaboratorResponse(CollaboratorBase):
    user_id: UUID
    username: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CollaboratorResponseUpdate(BaseModel):
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    role: Optional[str] = None
    can_edit: Optional[bool] = None
    created_at: Optional[datetime] = None
    contribution_description: Optional[str] = None
    contribution: Optional[str] = None
    message: Optional[str] = None


# Portfolio Schemas
class PortfolioBase(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = True
    is_default: Optional[bool] = False
    cover_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioCreate(PortfolioBase):
    user_id: UUID


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    is_default: Optional[bool] = None
    cover_image_url: Optional[str] = None


# Forward declarations for response models
class PortfolioProjectResponse(PortfolioProject):
    pass


class UserResponse(DBUser):
    profile: Optional[UserProfileRequest] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class Portfolio(PortfolioBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioResponse(Portfolio):
    projects: List[PortfolioProjectResponse] = Field(default_factory=list)
    project_count: int = Field(default=0)
    owner: Optional[UserResponse] = None
    cover_image_thumbnail: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Portfolio Project Association Schemas
class PortfolioProjectAssociationBase(BaseModel):
    position: Optional[int] = 0
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioProjectAssociationCreate(PortfolioProjectAssociationBase):
    portfolio_id: UUID
    project_id: UUID


class PortfolioProjectAssociationUpdate(BaseModel):
    position: Optional[int] = None
    notes: Optional[str] = None


class PortfolioProjectAssociation(PortfolioProjectAssociationBase):
    portfolio_id: UUID
    project_id: UUID
    added_at: datetime
    portfolio: Optional[Portfolio] = None
    project: Optional[PortfolioProject] = None

    model_config = ConfigDict(from_attributes=True)


# Custom Section Schemas
class CustomSectionBase(BaseModel):
    section_type: str  # 'timeline', 'gallery', 'testimonials', 'publications'
    title: str
    description: Optional[str] = None
    position: int
    is_visible: bool = True

    model_config = ConfigDict(from_attributes=True)


class CustomSectionCreate(CustomSectionBase):
    user_id: UUID


class CustomSectionUpdate(BaseModel):
    section_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    position: Optional[int] = None
    is_visible: Optional[bool] = None


class CustomSection(CustomSectionBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


# Custom Section Item Schemas
class CustomSectionItemBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    media_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CustomSectionItemCreate(CustomSectionItemBase):
    section_id: UUID


class CustomSectionItemUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    media_url: Optional[str] = None


class CustomSectionItem(CustomSectionItemBase):
    id: UUID
    section_id: UUID

    model_config = ConfigDict(from_attributes=True)


# Education Schemas
class EducationBase(BaseModel):
    user_id: Optional[UUID] = None
    id: Optional[UUID] = None
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: bool = False
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EducationCreate(EducationBase):
    user_id: Optional[UUID] = None


class EducationUpdate(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: Optional[bool] = None
    description: Optional[str] = None




# Content Block Schemas
class ContentBlockBase(BaseModel):
    id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    block_type: str  # 'about', 'services', 'process', 'fun_facts'
    title: Optional[str] = None
    content: str
    position: int
    is_visible: bool = False

    model_config = ConfigDict(from_attributes=True)


class ContentBlockCreate(ContentBlockBase):
    pass


class ContentBlockUpdate(BaseModel):
    block_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    position: Optional[int] = None
    is_visible: Optional[bool] = None

    

# Testimonial Schemas
class TestimonialBase(BaseModel):
    author_name: str
    author_title: Optional[str] = None
    author_company: Optional[str] = None
    author_relationship: Optional[str] = None  # "Colleague", "Manager", "Client"
    content: str
    rating: Optional[int] = Field(None, ge=1, le=5)  # 1-5 scale with validation
    is_approved: bool = False

    model_config = ConfigDict(from_attributes=True)


class TestimonialCreate(TestimonialBase):
    user_id: UUID  # Required - testimonial target user
    author_user_id: UUID  # Required - who is creating the testimonial


class TestimonialUpdate(BaseModel):
    author_name: Optional[str] = None
    author_title: Optional[str] = None
    author_company: Optional[str] = None
    author_relationship: Optional[str] = None
    content: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    is_approved: Optional[bool] = None


class Testimonial(TestimonialBase):
    id: UUID
    user_id: UUID  # Who the testimonial is for
    author_user_id: UUID  # Who created the testimonial
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# User Project Association Schemas
class UserProjectAssociationBase(BaseModel):
    role: Optional[str] = None
    can_edit: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class UserProjectAssociationCreate(UserProjectAssociationBase):
    user_id: UUID
    project_id: UUID


class UserProjectAssociationUpdate(BaseModel):
    role: Optional[str] = None
    can_edit: Optional[bool] = None


class UserProjectAssociation(UserProjectAssociationBase):
    user_id: UUID
    project_id: UUID
    created_at: datetime
    project: Optional[PortfolioProject] = None
    user: Optional[DBUser] = None

    model_config = ConfigDict(from_attributes=True)


# Project Like Schemas
class ProjectLikeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectLikeCreate(ProjectLikeBase):
    project_id: UUID
    user_id: UUID


class ProjectLike(ProjectLikeBase):
    id: UUID
    project_id: UUID
    user_id: UUID
    created_at: datetime
    user: DBUser  # Add user information

    model_config = ConfigDict(from_attributes=True)


# Project Comment Schemas
class ProjectCommentBase(BaseModel):
    content: str
    parent_comment_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectCommentCreate(ProjectCommentBase):
    project_id: UUID
    user_id: UUID


class ProjectCommentUpdate(BaseModel):
    content: Optional[str] = None


class ProjectComment(ProjectCommentBase):
    id: UUID
    project_id: UUID
    user_id: UUID
    created_at: datetime
    user: DBUser  # Add user information
    replies: Optional[List["ProjectComment"]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Project Audit Schemas
class ProjectAuditBase(BaseModel):
    action: str
    details: Optional[dict] = None  # JSON field becomes dict in Pydantic
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectAuditCreate(ProjectAuditBase):
    project_id: UUID
    user_id: UUID


class ProjectAuditUpdate(BaseModel):
    action: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ProjectAudit(ProjectAuditBase):
    id: UUID
    project_id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationBase(BaseModel):
    message: str = Field(..., max_length=255)
    notification_type: Optional[str] = "system"
    action_url: Optional[str] = Field(None, max_length=512)


class NotificationCreate(NotificationBase):
    # user_id: Optional[UUID] = None  # Or int if using integer IDs
    actor_id: Optional[UUID] = None
    meta_data: Optional[Dict[str, Any]] = Field(None)


class NotificationUpdate(BaseModel):
    is_read: bool = Field(True, description="Toggle read status")


class NotificationOut(NotificationBase):
    id: UUID
    user_id: Optional[UUID]
    actor_id: Optional[UUID]
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]
    meta_data: Optional[dict]  # JSON parsed to dict

    class Config:
        orm_mode = True  # Enable ORM compatibility


# Rebuild models to resolve forward references
ProjectComment.model_rebuild()
PortfolioResponse.model_rebuild()
PortfolioProjectResponse.model_rebuild()
UserResponse.model_rebuild()
