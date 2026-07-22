"""SQLAlchemy 2 models for SPWS hybrid storage (D011)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class RawSourceRow(Base):
    __tablename__ = "raw_sources"

    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    input_package_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_digest: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    storage_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    manuscript_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    version_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_version_ids: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    payload_json: Mapped[dict[str, Any] | str | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ManuscriptVersionRow(Base):
    __tablename__ = "manuscript_versions"

    version_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    manuscript_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    content_digest: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parent_version_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkPlanRow(Base):
    __tablename__ = "work_plans"

    plan_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    manuscript_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    version_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_version_ids: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RevisionDecisionRow(Base):
    __tablename__ = "revision_decisions"

    decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    manuscript_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    version_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_version_ids: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RunRow(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    manuscript_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    version_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_version_ids: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InputPackageRow(Base):
    """Kept for WorkspaceStore compatibility."""

    __tablename__ = "input_packages"

    package_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload_json: Mapped[str | dict[str, Any]] = mapped_column(Text, nullable=False)
