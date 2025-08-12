from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Float,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Book(Base):
    __tablename__ = "books"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    chapters = relationship("Chapter", back_populates="book")


class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(String, primary_key=True)
    book_id = Column(
        String,
        ForeignKey("books.id"),
        nullable=False,
        index=True,
    )
    index = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    text_sha256 = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="new")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    book = relationship("Book", back_populates="chapters")

    __table_args__ = (
        UniqueConstraint("book_id", "index", name="uq_chapter_book_index"),
        Index("ix_chapters_book_chapter", "book_id", "id"),
    )


class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(String, primary_key=True)
    book_id = Column(String, nullable=False, index=True)
    chapter_id = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    records = Column(JSON, nullable=False)
    stats = Column(JSON, nullable=True)
    text_sha256 = Column(String, nullable=False)
    params_sha256 = Column(String, nullable=False)
    status = Column(String, nullable=False, default="new")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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
    __tablename__ = "characters"
    id = Column(String, primary_key=True)
    book_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    aliases = Column(JSON, nullable=True)
    profile = Column(JSON, nullable=True)


class TTSProfile(Base):
    __tablename__ = "tts_profiles"
    id = Column(String, primary_key=True)
    character_id = Column(String, ForeignKey("characters.id"), nullable=False)
    engine = Column(String, nullable=False)
    settings = Column(JSON, nullable=True)


class Stem(Base):
    __tablename__ = "stems"
    id = Column(String, primary_key=True)
    book_id = Column(String, nullable=False, index=True)
    chapter_id = Column(String, nullable=False, index=True)
    utterance_idx = Column(Integer, nullable=False)
    path = Column(Text, nullable=False)
    duration_s = Column(Float, nullable=True)
    tts_profile_id = Column(String, nullable=True)
    hashes = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="new")

    __table_args__ = (
        Index(
            "ix_stems_book_chapter_utt",
            "book_id",
            "chapter_id",
            "utterance_idx",
        ),
    )


class Render(Base):
    __tablename__ = "renders"
    id = Column(String, primary_key=True)
    book_id = Column(String, nullable=False, index=True)
    chapter_id = Column(String, nullable=False, index=True)
    path = Column(Text, nullable=False)
    loudness_lufs = Column(Float, nullable=True)
    peak_dbfs = Column(Float, nullable=True)
    duration_s = Column(Float, nullable=True)
    hashes = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="new")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    book_id = Column(String, nullable=True, index=True)
    chapter_id = Column(String, nullable=True, index=True)
    stage = Column(String, nullable=True)
    params = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    logs_ptr = Column(Text, nullable=True)


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(String, primary_key=True)
    scope = Column(String, nullable=False)
    key = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
