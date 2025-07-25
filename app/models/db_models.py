from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Date,
    Text,
    Boolean,
    Index,
    JSON,
    UniqueConstraint,
    Enum,
)
from sqlalchemy.sql import func
from .base import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
import enum
from sqlalchemy.dialects.postgresql import ENUM


class User(Base):  # Done
    __tablename__ = "users"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    auth_id = Column(String, nullable=True, unique=True, default="")
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    firstname = Column(String, index=True, nullable=True)
    middlename = Column(String, index=True, nullable=True)
    lastname = Column(String, index=True, nullable=True)
    profile_picture = Column(String, nullable=True)
    profile_picture_id = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)
    role = Column(String, default="user")
    hashed_password = Column(String)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    settings = relationship(
        "UserSettings",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    skills = relationship("ProfessionalSkills", back_populates="user")
    social_links = relationship("SocialLinks", back_populates="user")
    certifications = relationship("Certification", back_populates="user")
    media_items = relationship("MediaGallery", back_populates="user")
    custom_sections = relationship("CustomSection", back_populates="user")
    education = relationship("Education", back_populates="user")
    content_blocks = relationship("ContentBlock", back_populates="user")
    devices = relationship(
        "UserDevices", back_populates="user", cascade="all, delete-orphan"
    )

    # Project relationships
    project_associations = relationship(
        "UserProjectAssociation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    projects = association_proxy("project_associations", "project")

    # Portfolio relationships
    portfolios = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )

    # Testimonial relationships
    testimonials = relationship(
        "Testimonial", back_populates="user", foreign_keys="[Testimonial.user_id]"
    )
    authored_testimonials = relationship(
        "Testimonial",
        foreign_keys="[Testimonial.author_user_id]",
        viewonly=True,
    )
    notifications = relationship(
        "Notification",
        foreign_keys="[Notification.user_id]",  # Explicitly use user_id as the foreign key
        back_populates="user",
    )
    suggestions = relationship(
        "Suggestion",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Suggestion.created_at.desc()",
    )

    suggestion_comments = relationship(
        "SuggestionComment", back_populates="user", cascade="all, delete-orphan"
    )

    suggestion_votes = relationship(
        "SuggestionVote", back_populates="user", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        email: str,
        auth_id: str,
        username: str,
        is_superuser: bool,
        hashed_password: str,
        firstname: str = "",
        middlename: str = "",
        lastname: str = "",
        is_active: bool = True,
        is_visible: bool = True,
        role: str = "user",
        id: Optional[uuid.UUID] = None,
        profile_picture: Optional[str] = None,
        profile_picture_id: Optional[str] = None,
    ):
        self.email = email
        self.auth_id = auth_id
        self.username = username
        self.firstname = firstname
        self.middlename = middlename
        self.lastname = lastname
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.is_superuser = is_superuser
        self.is_visible = is_visible
        self.role = role
        self.profile_picture = profile_picture
        self.profile_picture_id = profile_picture_id    
        self.id = id if id else uuid.uuid4()

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class UserSettings(Base):  # done
    __tablename__ = "user_settings"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    language = Column(String, index=True, default="en")
    loader = Column(
        String,
        nullable=True,
        default="portfolio-pro",
    )
    theme = Column(String, default="custom")  # 'light', 'dark', 'custom'
    primary_theme = Column(String, default="#171717")
    secondary_theme = Column(String, default="#ffffff")
    accent = Column(String, default="#05df72")
    primary_theme_dark = Column(String, default="#ededed")
    secondary_theme_dark = Column(String, default="#0a0a0a")
    layout_style = Column(
        String, default="modern"
    )  # 'modern', 'creative', 'minimalist'
    owner_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(id={self.id}, owner_id={self.owner_id})>"


class PortfolioProject(Base):  # done
    __tablename__ = "portfolio_projects"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    project_name = Column(String, nullable=False)
    project_description = Column(String, nullable=True)
    project_category = Column(String, nullable=True)
    project_url = Column(String, nullable=True)
    is_completed = Column(Boolean, nullable=True, default=False)
    is_concept = Column(Boolean, nullable=True, default=False)
    project_image_url = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_public = Column(Boolean, default=True)

    # FIXED: Corrected relationship name to match association model
    user_associations = relationship(
        "UserProjectAssociation",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    users = association_proxy("user_associations", "user")

    # Social features
    likes = relationship(
        "ProjectLike", back_populates="project", cascade="all, delete-orphan"
    )
    comments = relationship(
        "ProjectComment", back_populates="project", cascade="all, delete-orphan"
    )

    # Audit logs
    audit_logs = relationship(
        "ProjectAudit",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectAudit.created_at.desc()",
    )

    # Portfolio associations
    portfolio_associations = relationship(
        "PortfolioProjectAssociation",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    portfolios = association_proxy("portfolio_associations", "portfolio")

    def __repr__(self):
        return f"<PortfolioProject(id={self.id}, project_name={self.project_name})>"


class Portfolio(Base):  # done
    __tablename__ = "portfolios"
    __table_args__ = (
        Index("idx_portfolio_user", "user_id"),
        UniqueConstraint("user_id", "slug", name="uq_user_portfolio_slug"),
        {"schema": "portfolio_pro_app"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"), nullable=False
    )
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True, index=True)
    is_default = Column(Boolean, default=False)
    cover_image_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="portfolios")
    project_associations = relationship(
        "PortfolioProjectAssociation",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="PortfolioProjectAssociation.position",
    )
    # Association proxy for direct project access
    projects = association_proxy("project_associations", "project")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "slug" not in kwargs and "name" in kwargs:
            self.slug = self._generate_slug(kwargs["name"])

    def _generate_slug(self, name):
        # Simple slug generation - consider more robust solution
        import re

        base_slug = re.sub(r"[^a-zA-Z0-9\-_]", "-", name.lower())
        base_slug = re.sub(r"-+", "-", base_slug).strip("-")
        return f"{base_slug}-{str(uuid.uuid4())[:8]}"


class PortfolioProjectAssociation(Base):  # done
    __tablename__ = "portfolio_project_associations"
    __table_args__ = (
        Index("idx_portfolio_project", "portfolio_id", "project_id"),
        Index("idx_portfolio_order", "portfolio_id", "position"),
        {"schema": "portfolio_pro_app"},
    )

    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolio_pro_app.portfolios.id"),
        primary_key=True,
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolio_pro_app.portfolio_projects.id"),
        primary_key=True,
    )
    position = Column(Integer, default=0)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String(255), nullable=True)

    # Bidirectional relationships
    portfolio = relationship("Portfolio", back_populates="project_associations")
    project = relationship("PortfolioProject", back_populates="portfolio_associations")


class UserProfile(Base):  # done
    __tablename__ = "user_profile"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    github_username = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    profession = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    years_of_experience = Column(Integer, nullable=True)
    website_url = Column(String, nullable=True)
    location = Column(String, nullable=True)
    open_to_work = Column(Boolean, default=False)
    availability = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"


class ProfessionalSkills(Base):  # done
    __tablename__ = "professional_skills"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    skill_name = Column(String, nullable=False)
    proficiency_level = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user = relationship("User", back_populates="skills")

    def __repr__(self):
        return f"<ProfessionalSkills(id={self.id}, user_id={self.user_id}, skill_name={self.skill_name})>"


class SocialLinks(Base):  # done
    __tablename__ = "social_links"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    platform_name = Column(String, nullable=False)
    profile_url = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user = relationship("User", back_populates="social_links")

    def __repr__(self):
        return f"<SocialLinks(id={self.id}, user_id={self.user_id}, platform_name={self.platform_name})>"


class Certification(Base):  # done
    __tablename__ = "certifications"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    certification_name = Column(String, nullable=False)
    issuing_organization = Column(String, nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    user = relationship("User", back_populates="certifications")


class MediaGallery(Base):  # done
    __tablename__ = "media_gallery"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    media_type = Column(String, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="media_items")


class CustomSection(Base):  # done
    __tablename__ = "custom_sections"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    section_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    position = Column(Integer, nullable=False)
    is_visible = Column(Boolean, default=True)

    user = relationship("User", back_populates="custom_sections")
    items = relationship("CustomSectionItem", back_populates="section")


class CustomSectionItem(Base):  # done
    __tablename__ = "custom_section_items"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    section_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolio_pro_app.custom_sections.id")
    )
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    description = Column(String, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=False)
    media_url = Column(String, nullable=True)

    section = relationship("CustomSection", back_populates="items")


class Education(Base):  # done
    __tablename__ = "education"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    institution = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    field_of_study = Column(String, nullable=True)
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)
    is_current = Column(Boolean, default=False)
    description = Column(String, nullable=True)

    user = relationship("User", back_populates="education")


class ContentBlock(Base):  # done
    __tablename__ = "content_blocks"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    block_type = Column(String, nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)
    is_visible = Column(Boolean, default=False)

    user = relationship("User", back_populates="content_blocks")


class Testimonial(Base):  # done
    __tablename__ = "testimonials"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    author_user_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id")
    )
    author_name = Column(String, nullable=False)
    author_title = Column(String, nullable=True)
    author_company = Column(String, nullable=True)
    author_relationship = Column(String, nullable=True)
    content = Column(String, nullable=False)
    rating = Column(Integer, nullable=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="testimonials", foreign_keys=[user_id])
    author = relationship("User", viewonly=True, foreign_keys=[author_user_id])


class UserDevices(Base):  # done
    __tablename__ = "user_devices"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    device_name = Column(String, nullable=False)
    device_type = Column(String, nullable=False)
    last_used = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="devices")

    def __repr__(self):
        return f"<UserDevices(id={self.id}, user_id={self.user_id}, device_name={self.device_name})>"


class UserProjectAssociation(Base):  # done
    __tablename__ = "user_project_association"
    __table_args__ = (
        Index("idx_user_project_user_id", "user_id"),
        Index("idx_user_project_project_id", "project_id"),
        {"schema": "portfolio_pro_app"},
    )

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"), primary_key=True
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolio_pro_app.portfolio_projects.id"),
        primary_key=True,
    )
    role = Column(String, nullable=True)
    contribution = Column(String, nullable=True)
    contribution_description = Column(Text, nullable=True)
    can_edit = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="project_associations")
    # FIXED: Changed to match the corrected relationship name in PortfolioProject
    project = relationship("PortfolioProject", back_populates="user_associations")


class ProjectLike(Base):  # done
    __tablename__ = "project_likes"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolio_pro_app.portfolio_projects.id")
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("PortfolioProject", back_populates="likes")
    user = relationship("User")


class ProjectComment(Base):  # done
    __tablename__ = "project_comments"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolio_pro_app.portfolio_projects.id")
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    parent_comment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolio_pro_app.project_comments.id"),
        nullable=True,
    )

    project = relationship("PortfolioProject", back_populates="comments")
    user = relationship("User")
    replies = relationship(
        "ProjectComment", back_populates="parent_comment", remote_side=[id]
    )
    parent_comment = relationship(
        "ProjectComment", back_populates="replies", remote_side=[parent_comment_id]
    )


class ProjectAudit(Base):  # done
    __tablename__ = "project_audit_logs"
    __table_args__ = (
        Index("idx_project_audit_project_id", "project_id"),
        Index("idx_project_audit_user_id", "user_id"),
        Index("idx_project_audit_action", "action"),
        {"schema": "portfolio_pro_app"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolio_pro_app.portfolio_projects.id"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"), nullable=False
    )
    action = Column(String(50), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("PortfolioProject", back_populates="audit_logs")
    user = relationship("User")


class Notification(Base):  # done
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notification_user_unread", "user_id", "is_read"),
        Index("idx_notification_created", "created_at"),
        {"schema": "portfolio_pro_app"},  # Add this line
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID, ForeignKey("portfolio_pro_app.users.id"), nullable=False
    )  # Add schema prefix
    actor_id = Column(
        UUID, ForeignKey("portfolio_pro_app.users.id"), nullable=True
    )  # Add schema prefix
    message = Column(String(255), nullable=False)
    notification_type = Column(
        String(20), default="alert", nullable=False  # Adjust length as needed
    )
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    read_at = Column(DateTime, nullable=True)
    meta_data = Column(JSON, nullable=True)
    action_url = Column(String(512), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    actor = relationship("User", foreign_keys=[actor_id])


class Suggestion(Base):
    __tablename__ = "suggestions"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(
        String(20), default="pending"
    )  # pending/approved/rejected/implemented
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User")
    comments = relationship("SuggestionComment", back_populates="suggestion")
    votes = relationship("SuggestionVote", back_populates="suggestion")


class SuggestionComment(Base):
    __tablename__ = "suggestion_comments"
    __table_args__ = {"schema": "portfolio_pro_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suggestion_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolio_pro_app.suggestions.id")
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    content = Column(Text, nullable=False)
    parent_comment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolio_pro_app.suggestion_comments.id"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    suggestion = relationship("Suggestion", back_populates="comments")
    user = relationship("User")
    replies = relationship(
        "SuggestionComment", back_populates="parent_comment", remote_side=[id]
    )
    parent_comment = relationship(
        "SuggestionComment", back_populates="replies", remote_side=[parent_comment_id]
    )


class SuggestionVote(Base):
    __tablename__ = "suggestion_votes"
    __table_args__ = (
        UniqueConstraint("user_id", "suggestion_id", name="uq_user_suggestion_vote"),
        {"schema": "portfolio_pro_app"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    suggestion_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolio_pro_app.suggestions.id")
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    suggestion = relationship("Suggestion", back_populates="votes")
