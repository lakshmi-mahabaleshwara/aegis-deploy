"""SQLAlchemy models for the Identity Vault.

The Identity Vault stores the mapping between original patient identifiers
and their de-identified tokens. It is placed in a strictly isolated private
subnet and is never exposed to analytics users.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for vault models."""

    pass


class IdentityMapping(Base):
    """Maps an original identifier to its de-identified token.

    Attributes:
        id: Auto-incrementing primary key.
        original_id: The original patient/study identifier (e.g. DICOM PatientID,
            S3 key). Unique — each original can map to exactly one token.
        deid_token: The deterministic de-identified token (SHA-256 hash output).
        modality: Imaging modality (CT, MR, US, etc.) if available.
        source_type: Origin storage (``s3`` or ``healthimaging``).
        batch_id: ID of the processing batch that created this mapping.
        created_at: UTC timestamp of record creation.
    """

    __tablename__ = "identity_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_id = Column(String(512), nullable=False, unique=True, index=True)
    deid_token = Column(String(128), nullable=False, index=True)
    modality = Column(String(16), nullable=True)
    source_type = Column(String(32), nullable=False, default="s3")
    batch_id = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_identity_batch", "batch_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<IdentityMapping(original_id='{self.original_id[:20]}...', "
            f"token='{self.deid_token[:16]}...')>"
        )


class AuditLog(Base):
    """Audit trail for vault operations.

    Records every access to the Identity Vault for compliance.

    Attributes:
        id: Auto-incrementing primary key.
        action: Type of operation (``create``, ``lookup``, ``re_identify``).
        actor: Identifier of the service/user performing the action.
        original_id: Original ID involved (nullable for bulk ops).
        details: Free-text details or JSON payload.
        timestamp: UTC timestamp of the action.
    """

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(64), nullable=False)
    actor = Column(String(128), nullable=False, default="aegis-deploy")
    original_id = Column(String(512), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
