"""Database tables. One organisation per deployment keeps the MVP simple;
every table would gain an org_id column for multi-organisation use."""
from datetime import datetime, date
from sqlalchemy import String, Text, Integer, Float, DateTime, Date, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def now():
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    role: Mapped[str] = mapped_column(String(20))  # admin | creator | reviewer
    password_hash: Mapped[str] = mapped_column(String(300))


# ---------- Brand knowledge ----------
class Rule(Base):
    """One guideline rule. Edited rules bump `version` so findings stay traceable."""
    __tablename__ = "rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    category: Mapped[str] = mapped_column(String(30))  # tone|claim|term|visual|accessibility|messaging
    text: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(12), default="major")
    version: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(200), default="manual")
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Fact(Base):
    """Claims Ledger entry: an approved fact with an optional validity date."""
    __tablename__ = "facts"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(String(200))
    value_type: Mapped[str] = mapped_column(String(12))  # price|percent|number|claim
    keywords: Mapped[str] = mapped_column(String(300))   # comma separated
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Term(Base):
    __tablename__ = "terms"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    preferred: Mapped[str] = mapped_column(String(120), default="")  # empty = remove
    variants: Mapped[str] = mapped_column(String(400))  # comma separated wrong/banned forms
    note: Mapped[str] = mapped_column(String(300), default="")
    severity: Mapped[str] = mapped_column(String(12), default="major")


class PaletteColor(Base):
    __tablename__ = "palette"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    hex: Mapped[str] = mapped_column(String(7))


# ---------- Content & workflow ----------
class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)


class Content(Base):
    __tablename__ = "contents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10))  # text|pdf|docx|image
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    creator = relationship("User")
    campaign = relationship("Campaign")


class Version(Base):
    __tablename__ = "versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    colors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    lane: Mapped[str] = mapped_column(String(10))      # verified | advisory
    category: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(12))  # blocking | major | minor
    quote: Mapped[str] = mapped_column(Text, default="")
    start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_code: Mapped[str] = mapped_column(String(20), default="")
    rule_version: Mapped[int] = mapped_column(Integer, default=1)
    rule_text: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    replacement: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="open")  # open|accepted|dismissed|overridden
    resolution_note: Mapped[str] = mapped_column(Text, default="")
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    target: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    user = relationship("User")


class UncoveredIssue(Base):
    """An issue the AI noticed that no stored rule covers -> a 'missing rule' gap signal."""
    __tablename__ = "uncovered_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    quote: Mapped[str] = mapped_column(Text, default="")
    issue: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
