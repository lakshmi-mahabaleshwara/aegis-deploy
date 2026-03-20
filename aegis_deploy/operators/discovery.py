"""Discovery Operator — the 'Scout' that scans raw storage for new data.

Scans S3 and AWS HealthImaging for new files since the last run,
cross-references the Identity Vault to identify delta (unprocessed) items,
and produces a JSON manifest for downstream workers.
"""

import logging
from datetime import datetime, timezone

import boto3

from aegis_deploy.operators.manifest import Manifest, ManifestItem

logger = logging.getLogger(__name__)

# Known DICOM extensions
_DICOM_EXTENSIONS = {".dcm", ".dicom"}
# Known image extensions
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class DiscoveryOperator:
    """Scans raw storage and generates a processing manifest.

    Args:
        config: Fully resolved deploy configuration dictionary.
    """

    def __init__(self, config: dict):
        self.config = config
        self.storage_config = config.get("storage", {}).get("raw", {})
        self.batch_size = config.get("discovery", {}).get("batch_size", 500)
        self._s3_client = None

    @property
    def s3_client(self):
        """Lazy-initialized S3 client."""
        if self._s3_client is None:
            region = self.config.get("aws", {}).get("region", "us-east-1")
            self._s3_client = boto3.client("s3", region_name=region)
        return self._s3_client

    def scan(self) -> Manifest:
        """Scan all raw storage sources and produce a manifest.

        Returns:
            A ``Manifest`` containing all new/unprocessed items found.
        """
        batch_id = Manifest.generate_batch_id()
        logger.info("Discovery scan starting — batch_id=%s", batch_id)

        items: list[ManifestItem] = []

        # Scan S3 raw bucket
        s3_items = self._scan_s3()
        items.extend(s3_items)

        # Scan AWS HealthImaging (if configured)
        hi_items = self._scan_healthimaging()
        items.extend(hi_items)

        # Filter out already-processed items via Identity Vault
        delta_items = self._filter_delta(items)

        # Respect batch size limit
        if len(delta_items) > self.batch_size:
            logger.info(
                "Trimming to batch_size=%d (found %d items)",
                self.batch_size,
                len(delta_items),
            )
            delta_items = delta_items[: self.batch_size]

        manifest = Manifest(
            batch_id=batch_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            items=delta_items,
        )

        logger.info(
            "Discovery complete: %d S3, %d HealthImaging, %d delta (after vault filter)",
            len(s3_items),
            len(hi_items),
            len(delta_items),
        )
        return manifest

    def _scan_s3(self) -> list[ManifestItem]:
        """List objects in the raw S3 bucket and group into manifest items.

        Groups files by prefix (folder) as series, or treats individual files
        as standalone items.
        """
        s3_config = self.storage_config.get("s3", {})
        bucket = s3_config.get("bucket", "")
        prefix = s3_config.get("prefix", "incoming/")

        if not bucket:
            logger.warning("No raw S3 bucket configured — skipping S3 scan")
            return []

        items = []
        folders: dict[str, list[str]] = {}

        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]

                    # Skip directory markers
                    if key.endswith("/"):
                        continue

                    # Determine parent folder (one level below prefix)
                    relative = key[len(prefix) :]
                    parts = relative.split("/")

                    if len(parts) > 1:
                        # File is inside a subfolder → group as series
                        folder_name = parts[0]
                        folders.setdefault(folder_name, []).append(key)
                    else:
                        # Loose file → individual item
                        ext = "." + key.rsplit(".", 1)[-1].lower() if "." in key else ""
                        items.append(
                            ManifestItem(
                                item_type="individual",
                                source="s3",
                                paths=[key],
                                metadata={"file_type": "dicom" if ext in _DICOM_EXTENSIONS else "image"},
                            )
                        )

            # Convert grouped folders to series items
            for folder_name, keys in folders.items():
                items.append(
                    ManifestItem(
                        item_type="series",
                        source="s3",
                        paths=sorted(keys),
                        metadata={"folder": folder_name},
                    )
                )

        except Exception as e:
            logger.error("S3 scan failed: %s", e, exc_info=True)

        logger.info("S3 scan: %d items from s3://%s/%s", len(items), bucket, prefix)
        return items

    def _scan_healthimaging(self) -> list[ManifestItem]:
        """Scan AWS HealthImaging for DICOM studies.

        Uses the medical-imaging service client to list image sets
        in the configured datastore.
        """
        hi_config = self.storage_config.get("healthimaging", {})
        datastore_id = hi_config.get("datastore_id", "")

        if not datastore_id:
            logger.debug("No HealthImaging datastore configured — skipping")
            return []

        items = []

        try:
            region = self.config.get("aws", {}).get("region", "us-east-1")
            hi_client = boto3.client("medical-imaging", region_name=region)

            response = hi_client.list_image_set_versions(
                datastoreId=datastore_id,
            )

            for image_set in response.get("imageSetPropertiesList", []):
                image_set_id = image_set.get("imageSetId", "")
                items.append(
                    ManifestItem(
                        item_type="series",
                        source="healthimaging",
                        paths=[f"healthimaging://{datastore_id}/{image_set_id}"],
                        metadata={
                            "datastore_id": datastore_id,
                            "image_set_id": image_set_id,
                        },
                    )
                )

        except Exception as e:
            logger.error("HealthImaging scan failed: %s", e, exc_info=True)

        logger.info("HealthImaging scan: %d image sets", len(items))
        return items

    def _filter_delta(self, items: list[ManifestItem]) -> list[ManifestItem]:
        """Filter out items that have already been processed.

        Cross-references the Identity Vault to find items whose primary path
        has already been de-identified in a previous batch.

        In production, this connects to the VaultRepository:
            from aegis_deploy.vault.repository import VaultRepository
            repo = VaultRepository(self.config.get("vault", {}))
            processed = repo.get_processed_ids()
            return [item for item in items if item.paths[0] not in processed]
        """
        # Stub: return all items (no vault connection yet)
        logger.debug("Delta filter: %d items (vault check stubbed)", len(items))
        return items
