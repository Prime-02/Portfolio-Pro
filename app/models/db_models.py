from sqlalchemy import Column, Integer, String, ForeignKey
from .base import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'schema': 'portfolio_pro_app'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    is_active = Column(Integer, default=0)
    role = Column(String, default="user")
    hashed_password = Column(String)
    settings = relationship(
        "UserSettings", 
        back_populates="user", 
        cascade="all, delete-orphan",
        uselist=False
    )

    def __init__(self, email: str, username: str, hashed_password: str,
                 is_active: bool = True, role: str = "user",
                 id: Optional[uuid.UUID] = None):
        self.email = email
        self.username = username
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.role = role
        self.id = id if id else uuid.uuid4()

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

class UserSettings(Base):
    __tablename__ = "user_settings"
    __table_args__ = {'schema': 'portfolio_pro_app'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    language = Column(String, index=True)
    theme = Column(String)
    primaryTheme = Column(String)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_pro_app.users.id"))
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(id={self.id}, owner_id={self.owner_id})>"