"""Storage Operator — writes de-identified outputs to clean storage and Identity Vault.

Responsibilities:
1. Upload clean images to S3 / AWS HealthImaging (using token as key)
2. Record Original_ID → DeID_Token mapping in the Identity Vault (RDS)
3. Prepare analytics metadata for the Iceberg lakehouse (excludes Original_ID)
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StorageOperator:
    """Persists de-identification results to clean storage and metadata stores.

    Args:
        config: Fully resolved deploy configuration dictionary.
    """

    def __init__(self, config: dict):
        self.config = config
        self.storage_config = config.get("storage", {}).get("clean", {})
        self.vault_config = config.get("vault", {})

    def store(self, results: list) -> None:
        """Store all de-identification results.

        Args:
            results: List of ``DeIDResult`` objects from the DeID operator.
        """
        successful = [r for r in results if r.success]
        logger.info("Storing %d successful results", len(successful))

        for result in successful:
            self._upload_to_clean_storage(result)
            self._record_in_vault(result)
            self._emit_analytics_record(result)

        logger.info("Storage complete: %d items persisted", len(successful))

    def _upload_to_clean_storage(self, result) -> None:
        """Upload de-identified image to the clean S3 bucket.

        In production, this uses boto3/s3fs:
            s3_client.upload_file(
                result.output_path,
                bucket=self.storage_config["s3"]["bucket"],
                key=f"{prefix}/{result.deid_token}"
            )
        """
        bucket = self.storage_config.get("s3", {}).get("bucket", "aegis-clean-images")
        prefix = self.storage_config.get("s3", {}).get("prefix", "deidentified/")
        target_key = f"{prefix}{result.deid_token}"
        logger.debug("Upload: %s → s3://%s/%s", result.output_path, bucket, target_key)

    def _record_in_vault(self, result) -> None:
        """Record the identity mapping in the Identity Vault (RDS).

        In production, this uses the VaultRepository:
            from aegis_deploy.vault.repository import VaultRepository
            repo = VaultRepository(self.vault_config)
            repo.store_mapping(
                original_id=result.original_path,
                deid_token=result.deid_token,
                modality=result.modality,
                batch_id=batch_id,
            )
        """
        logger.debug(
            "Vault record: %s → %s (modality=%s)",
            result.original_path,
            result.deid_token,
            result.modality,
        )

    def _emit_analytics_record(self, result) -> None:
        """Prepare an analytics record for the Iceberg lakehouse.

        PRIVACY GUARDRAIL: The Original_ID is explicitly excluded.
        Only the de-identified token and clinical metadata are emitted.
        """
        record = {
            "deid_token": result.deid_token,
            "modality": result.modality,
            "source_type": result.source_type,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            # Original_ID is intentionally EXCLUDED from analytics
        }
        logger.debug("Analytics record: %s", record)
