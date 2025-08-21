"""Database models.

Lightweight SQLAlchemy ORM models for books, chapters, annotations, audio
stems/renders, jobs and metrics. Field names are intentionally concise; any
additional per-record metadata lives inside JSON columns (e.g. ``meta`` or
``hashes``).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Project Declarative base class.

    Declaring an explicit subclass (rather than using ``declarative_base()``)
    gives mypy a concrete symbol it can understand as a valid base for ORM
    models, avoiding ``Variable ... is not valid as a type`` errors.
    """

    # Provide a common created_at/updated_at mixin later if desired.
    pass


class Book(Base):
    """Book level metadata and relationship to its chapters."""

    __tablename__ = "books"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    meta: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    chapters = relationship("Chapter", back_populates="book")


class Chapter(Base):
    """Single chapter unit with source payload and status flags."""

    __tablename__ = "chapters"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    book_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("books.id"),
        nullable=False,
        index=True,
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    book = relationship("Book", back_populates="chapters")

    __table_args__ = (
        UniqueConstraint("book_id", "index", name="uq_chapter_book_index"),
        Index("ix_chapters_book_chapter", "book_id", "id"),
    )


class Annotation(Base):
    """Stored annotation records (utterances, segmentation, stats)."""

    __tablename__ = "annotations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    book_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    chapter_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    records: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    stats: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    text_sha256: Mapped[str] = mapped_column(String, nullable=False)
    params_sha256: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_annotations_book_chapter",
            "book_id",
            "chapter_id",
        ),
    )


class Character(Base):
    """Character entity with optional aliases & profile blob."""

    __tablename__ = "characters"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    book_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    aliases: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    profile: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


class TTSProfile(Base):
    """Voice synthesis profile configuration for a character."""

    __tablename__ = "tts_profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    character_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("characters.id"),
        nullable=False,
    )
    engine: Mapped[str] = mapped_column(String, nullable=False)
    settings: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


class Stem(Base):
    """Atomic synthesized audio stem for an utterance within a chapter."""

    __tablename__ = "stems"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    book_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    chapter_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    utterance_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    tts_profile_id: Mapped[str | None] = mapped_column(String, nullable=True)
    hashes: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="new")

    __table_args__ = (
        Index(
            "ix_stems_book_chapter_utt",
            "book_id",
            "chapter_id",
            "utterance_idx",
        ),
    )


class Render(Base):
    """Chapter-level rendered / mixed audio artifact."""

    __tablename__ = "renders"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    book_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    chapter_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    loudness_lufs: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_dbfs: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    hashes: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="new")


class Job(Base):
    """Background job tracking (ingestion, synthesis, rendering, etc)."""

    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    book_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    chapter_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    stage: Mapped[str | None] = mapped_column(String, nullable=True)
    params: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    logs_ptr: Mapped[str | None] = mapped_column(Text, nullable=True)


class Metric(Base):
    """Simple time-series numeric metric (scoped by domain + key)."""

    __tablename__ = "metrics"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
