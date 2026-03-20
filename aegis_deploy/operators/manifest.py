"""Manifest — structured representation of a batch of images to process.

A manifest groups images into series (folders) or individual (loose) files,
enabling Argo fan-out parallelism across workers.
"""

import json
import logging
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class ManifestItem:
    """A single processable item in the manifest.

    Attributes:
        item_type: Whether this is a ``series`` (folder of related images)
            or an ``individual`` (single loose file).
        source: Origin storage system — ``s3`` or ``healthimaging``.
        paths: List of file paths / S3 keys belonging to this item.
        metadata: Optional metadata (modality, study description, etc.).
    """

    item_type: Literal["series", "individual"]
    source: Literal["s3", "healthimaging"]
    paths: list[str]
    metadata: dict = field(default_factory=dict)


@dataclass
class Manifest:
    """Batch manifest produced by the Discovery Operator.

    Attributes:
        batch_id: Unique identifier for this processing batch.
        created_at: ISO-8601 timestamp of manifest creation.
        items: List of ``ManifestItem`` objects to process.
    """

    batch_id: str
    created_at: str
    items: list[ManifestItem]

    def save(self, path: str) -> None:
        """Serialize the manifest to a JSON file.

        Args:
            path: File path to write the JSON manifest.
        """
        data = {
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "items": [asdict(item) for item in self.items],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Manifest saved: %s (%d items)", path, len(self.items))

    @classmethod
    def load(cls, path: str) -> "Manifest":
        """Deserialize a manifest from a JSON file.

        Args:
            path: File path to the JSON manifest.

        Returns:
            Manifest instance.
        """
        with open(path, "r") as f:
            data = json.load(f)
        items = [ManifestItem(**item) for item in data["items"]]
        return cls(
            batch_id=data["batch_id"],
            created_at=data["created_at"],
            items=items,
        )

    def fan_out(self, num_chunks: int) -> list[list[ManifestItem]]:
        """Split items into N roughly-equal chunks for parallel workers.

        Args:
            num_chunks: Number of parallel worker chunks.

        Returns:
            List of item lists, one per worker.
        """
        if num_chunks <= 0:
            num_chunks = 1
        chunk_size = math.ceil(len(self.items) / num_chunks)
        chunks = [
            self.items[i : i + chunk_size] for i in range(0, len(self.items), chunk_size)
        ]
        logger.info("Fan-out: %d items → %d chunks", len(self.items), len(chunks))
        return chunks

    @staticmethod
    def generate_batch_id() -> str:
        """Generate a unique batch ID based on the current timestamp."""
        return datetime.now(timezone.utc).strftime("batch-%Y%m%d-%H%M%S")
