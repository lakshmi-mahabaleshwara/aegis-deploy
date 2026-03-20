"""Aegis De-Identification MAP Application.

Composes the operator DAG: Discovery → DeID → Storage.
This is the top-level MONAI Deploy Application class that can be packaged
as a MAP container.
"""

import logging
from pathlib import Path

from aegis_deploy.config.config_loader import load_config
from aegis_deploy.map.deid_operator import DeIDOperator
from aegis_deploy.map.storage_operator import StorageOperator
from aegis_deploy.operators.manifest import Manifest

logger = logging.getLogger(__name__)


class AegisDeIDApp:
    """MONAI Deploy Application Package — orchestrates de-identification.

    In a full MONAI Deploy SDK integration this would extend
    ``monai.deploy.core.Application`` and use ``self.add_operator()`` to
    compose the DAG.  For now it provides a lightweight equivalent that can
    run standalone or inside an Argo worker pod.

    Args:
        config: Fully resolved configuration dictionary.
        manifest_path: Path to the JSON manifest produced by the Discovery
            Operator.
        chunk_index: If provided, process only this chunk of the manifest
            (used for Argo fan-out parallelism).
    """

    def __init__(self, config: dict, manifest_path: str, chunk_index: int | None = None):
        self.config = config
        self.manifest_path = manifest_path
        self.chunk_index = chunk_index

    def run(self):
        """Execute the de-identification pipeline."""
        logger.info("=== Aegis DeID App — Starting ===")

        # 1. Load manifest
        manifest = Manifest.load(self.manifest_path)
        logger.info("Loaded manifest: batch_id=%s, %d items", manifest.batch_id, len(manifest.items))

        # 2. Select chunk (for fan-out workers)
        if self.chunk_index is not None:
            chunks = manifest.fan_out(self.config.get("orchestration", {}).get("parallelism", 4))
            if self.chunk_index >= len(chunks):
                logger.warning(
                    "Chunk index %d out of range (total chunks: %d). Nothing to do.",
                    self.chunk_index,
                    len(chunks),
                )
                return
            items = chunks[self.chunk_index]
            logger.info("Processing chunk %d/%d (%d items)", self.chunk_index + 1, len(chunks), len(items))
        else:
            items = manifest.items
            logger.info("Processing all %d items (no fan-out)", len(items))

        # 3. Run de-identification
        deid_operator = DeIDOperator(self.config)
        results = deid_operator.process(items)

        # 4. Persist to clean storage + vault
        storage_operator = StorageOperator(self.config)
        storage_operator.store(results)

        logger.info(
            "=== Aegis DeID App — Complete (%d items processed) ===",
            len(results),
        )
