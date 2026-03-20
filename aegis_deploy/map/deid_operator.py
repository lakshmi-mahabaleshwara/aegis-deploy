"""De-Identification Operator — wraps the aegis core pipeline.

This MAP operator accepts manifest items (image paths + metadata) and runs
them through the aegis de-identification transforms (DICOM tag scrubbing,
UID remapping, OCR/PHI masking).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DeIDResult:
    """Result from de-identifying a single item."""

    original_path: str
    output_path: str
    deid_token: str
    modality: str | None = None
    source_type: str = "s3"  # "s3" or "healthimaging"
    metadata: dict = field(default_factory=dict)
    success: bool = True
    error: str | None = None


class DeIDOperator:
    """MAP Operator wrapping the aegis de-identification pipeline.

    Reads aegis pipeline configuration from the deploy config and delegates
    to ``monai_aegis`` build_pipeline / build_image_pipeline based on file type.

    Args:
        config: Fully resolved deploy configuration dictionary.
    """

    def __init__(self, config: dict):
        self.config = config
        self.aegis_config = config.get("aegis", {})

    def process(self, items: list) -> list[DeIDResult]:
        """Process a list of manifest items through aegis.

        Args:
            items: List of ``ManifestItem`` objects from the discovery manifest.

        Returns:
            List of ``DeIDResult`` objects with output paths and tokens.
        """
        results = []

        for item in items:
            try:
                result = self._process_item(item)
                results.append(result)
            except Exception as e:
                logger.error("Failed to process item %s: %s", item.paths, e, exc_info=True)
                results.append(
                    DeIDResult(
                        original_path=item.paths[0] if item.paths else "unknown",
                        output_path="",
                        deid_token="",
                        source_type=item.source,
                        success=False,
                        error=str(e),
                    )
                )

        succeeded = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        logger.info("DeID complete: %d succeeded, %d failed", succeeded, failed)

        return results

    def _process_item(self, item) -> DeIDResult:
        """Run aegis pipeline on a single manifest item.

        This method integrates with the aegis core library's pipeline builders:
        - DICOM files → build_pipeline / build_series_pipeline
        - Image files → build_image_pipeline / build_image_series_pipeline

        The actual aegis integration is stubbed here and should be connected
        to the installed monai_aegis package.
        """
        from aegis_deploy.operators.manifest import ManifestItem

        assert isinstance(item, ManifestItem)

        logger.info(
            "Processing: type=%s, source=%s, paths=%d",
            item.item_type,
            item.source,
            len(item.paths),
        )

        # --- Aegis Core Integration Point ---
        # In production, this calls into monai_aegis pipelines:
        #
        #   from monai_aegis.transforms.pipeline import build_pipeline, build_image_pipeline
        #   from monai_aegis.transforms.utility import AegisIdentityManager
        #
        #   identity_mgr = AegisIdentityManager(salt=self.aegis_config["tokenization"]["salt"])
        #   if item.item_type == "dicom":
        #       pipeline = build_pipeline(config, output_dir)
        #   else:
        #       pipeline = build_image_pipeline(config, output_dir)
        #   result = pipeline({"image": item.paths[0]})
        #
        # For now, we produce a placeholder result demonstrating the data flow.

        primary_path = item.paths[0]
        token = f"TOKEN_{hash(primary_path) & 0xFFFFFFFF:08x}"

        output_dir = self.aegis_config.get("paths", {}).get("output_dir", "/data/output")
        output_path = f"{output_dir}/{token}"

        return DeIDResult(
            original_path=primary_path,
            output_path=output_path,
            deid_token=token,
            modality=item.metadata.get("modality"),
            source_type=item.source,
            metadata=item.metadata,
        )
