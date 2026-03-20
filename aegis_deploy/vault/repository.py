"""Vault Repository — CRUD operations for the Identity Vault.

Provides a high-level interface over the Identity Vault database,
with connection pooling, audit logging, and batch operations.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from aegis_deploy.vault.models import AuditLog, Base, IdentityMapping

logger = logging.getLogger(__name__)


class VaultRepository:
    """Repository for Identity Vault operations.

    Args:
        config: Vault configuration dict with keys: host, port, database,
            username, password, pool_size, max_overflow.
    """

    def __init__(self, config: dict):
        self.config = config
        self._engine = None
        self._session_factory = None

    @property
    def engine(self):
        """Lazy-initialized SQLAlchemy engine."""
        if self._engine is None:
            url = self._build_connection_url()
            kwargs = {"pool_pre_ping": True}
            # pool_size / max_overflow are not supported by SQLite
            if not url.startswith("sqlite"):
                kwargs["pool_size"] = self.config.get("pool_size", 5)
                kwargs["max_overflow"] = self.config.get("max_overflow", 10)
            self._engine = create_engine(url, **kwargs)
        return self._engine

    @property
    def session_factory(self):
        """Lazy-initialized session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        return self._session_factory

    def _build_connection_url(self) -> str:
        """Build a PostgreSQL connection URL from config."""
        host = self.config.get("host", "localhost")
        port = self.config.get("port", "5432")
        database = self.config.get("database", "aegis_vault")
        username = self.config.get("username", "aegis")
        password = self.config.get("password", "")

        # Support SQLite for testing (when host is empty or ":memory:")
        if not host or host == ":memory:":
            return "sqlite:///:memory:"

        return f"postgresql://{username}:{password}@{host}:{port}/{database}"

    def initialize_schema(self) -> None:
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)
        logger.info("Vault schema initialized")

    def store_mapping(
        self,
        original_id: str,
        deid_token: str,
        modality: str | None = None,
        source_type: str = "s3",
        batch_id: str = "",
    ) -> IdentityMapping:
        """Store a new identity mapping (upsert — blind overwrite).

        Uses deterministic hashing, so duplicate original_ids will
        always produce the same token. On conflict, the existing
        record is returned without modification.

        Args:
            original_id: Original patient/study identifier.
            deid_token: De-identified token.
            modality: Imaging modality (optional).
            source_type: Origin storage system.
            batch_id: Processing batch identifier.

        Returns:
            The created or existing ``IdentityMapping`` record.
        """
        with self.session_factory() as session:
            # Check for existing mapping (deterministic hashing = idempotent)
            existing = session.execute(
                select(IdentityMapping).where(IdentityMapping.original_id == original_id)
            ).scalar_one_or_none()

            if existing:
                logger.debug("Mapping exists: %s → %s", original_id[:20], existing.deid_token[:16])
                return existing

            mapping = IdentityMapping(
                original_id=original_id,
                deid_token=deid_token,
                modality=modality,
                source_type=source_type,
                batch_id=batch_id,
            )
            session.add(mapping)

            # Audit log
            session.add(
                AuditLog(
                    action="create",
                    original_id=original_id,
                    details=f"token={deid_token}, batch={batch_id}",
                )
            )

            session.commit()
            logger.debug("Stored mapping: %s → %s", original_id[:20], deid_token[:16])
            return mapping

    def lookup_token(self, original_id: str) -> str | None:
        """Look up the de-identified token for an original ID.

        Args:
            original_id: The original identifier to look up.

        Returns:
            The de-identified token, or ``None`` if not found.
        """
        with self.session_factory() as session:
            mapping = session.execute(
                select(IdentityMapping).where(IdentityMapping.original_id == original_id)
            ).scalar_one_or_none()

            # Audit log
            session.add(
                AuditLog(
                    action="lookup",
                    original_id=original_id,
                    details=f"found={'yes' if mapping else 'no'}",
                )
            )
            session.commit()

            return mapping.deid_token if mapping else None

    def get_processed_ids(self) -> set[str]:
        """Return the set of all original IDs that have been processed.

        Used by the Discovery Operator to filter delta items.

        Returns:
            Set of original_id strings.
        """
        with self.session_factory() as session:
            result = session.execute(select(IdentityMapping.original_id))
            return {row[0] for row in result}

    def get_mapping_count(self) -> int:
        """Return the total number of identity mappings."""
        with self.session_factory() as session:
            from sqlalchemy import func

            result = session.execute(select(func.count(IdentityMapping.id)))
            return result.scalar_one()
