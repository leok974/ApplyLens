from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Index, ForeignKey, Enum, Float
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .db import Base
import enum

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True)
    provider = Column(String(32), nullable=False, index=True)  # "google"
    user_email = Column(String(320), nullable=False, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_uri = Column(Text, nullable=False)
    client_id = Column(Text, nullable=False)
    client_secret = Column(Text, nullable=False)
    scopes = Column(Text, nullable=False)
    expiry = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class GmailToken(Base):
    """Per-user Gmail OAuth tokens for multi-user support."""
    __tablename__ = "gmail_tokens"
    user_email = Column(String(255), primary_key=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=False)
    expiry_date = Column(Integer, nullable=True)  # milliseconds since epoch
    scope = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Email(Base):
    __tablename__ = "emails"
    id = Column(Integer, primary_key=True)
    gmail_id = Column(String(128), unique=True, index=True)
    thread_id = Column(String(128), index=True)
    subject = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    sender = Column(String(512), index=True)
    recipient = Column(String(512), index=True)
    received_at = Column(DateTime(timezone=True), index=True)
    labels = Column(ARRAY(String), nullable=True)
    label_heuristics = Column(ARRAY(String), nullable=True)
    raw = Column(JSON, nullable=True)

    # NEW quick hooks
    company = Column(String(256), index=True)
    role = Column(String(512), index=True)
    source = Column(String(128), index=True)
    source_confidence = Column(Float, default=0.0)

    # Reply metrics
    first_user_reply_at = Column(DateTime(timezone=True), nullable=True)
    last_user_reply_at = Column(DateTime(timezone=True), nullable=True)
    user_reply_count = Column(Integer, default=0)

    # Optional link to application
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    application = relationship("Application", back_populates="emails", foreign_keys=[application_id])

Index("idx_emails_search", Email.subject, Email.sender, Email.recipient)

class AppStatus(str, enum.Enum):
    applied = "applied"
    hr_screen = "hr_screen"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"
    on_hold = "on_hold"
    ghosted = "ghosted"

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    company = Column(String(256), index=True, nullable=False)
    role = Column(String(512), index=True)
    source = Column(String(128), index=True)
    source_confidence = Column(Float, default=0.0)

    # convenience linkage
    thread_id = Column(String(128), index=True)
    gmail_thread_id = Column(String(128), index=True)  # alias for consistency with patch
    last_email_id = Column(Integer, ForeignKey("emails.id"), nullable=True)
    last_email_snippet = Column(Text, nullable=True)

    status = Column(Enum(AppStatus), default=AppStatus.applied, nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    emails = relationship("Email", back_populates="application", foreign_keys="Email.application_id")
