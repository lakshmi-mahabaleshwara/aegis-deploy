"""Unit tests for the Manifest dataclass."""

import json
import os
import tempfile
import unittest

from aegis_deploy.operators.manifest import Manifest, ManifestItem


class TestManifestItem(unittest.TestCase):
    """Test ManifestItem creation and properties."""

    def test_create_individual(self):
        item = ManifestItem(
            item_type="individual",
            source="s3",
            paths=["incoming/scan001.dcm"],
        )
        self.assertEqual(item.item_type, "individual")
        self.assertEqual(item.source, "s3")
        self.assertEqual(len(item.paths), 1)
        self.assertEqual(item.metadata, {})

    def test_create_series(self):
        item = ManifestItem(
            item_type="series",
            source="healthimaging",
            paths=["hi://ds1/img1", "hi://ds1/img2"],
            metadata={"modality": "CT"},
        )
        self.assertEqual(item.item_type, "series")
        self.assertEqual(len(item.paths), 2)
        self.assertEqual(item.metadata["modality"], "CT")


class TestManifest(unittest.TestCase):
    """Test Manifest serialization, deserialization, and fan-out."""

    def _make_manifest(self, n_items: int = 10) -> Manifest:
        items = [
            ManifestItem(
                item_type="individual",
                source="s3",
                paths=[f"incoming/file_{i}.png"],
                metadata={"index": i},
            )
            for i in range(n_items)
        ]
        return Manifest(
            batch_id="batch-20260319-020000",
            created_at="2026-03-19T02:00:00+00:00",
            items=items,
        )

    def test_save_and_load_roundtrip(self):
        manifest = self._make_manifest(5)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            manifest.save(path)
            loaded = Manifest.load(path)
            self.assertEqual(loaded.batch_id, manifest.batch_id)
            self.assertEqual(len(loaded.items), 5)
            self.assertEqual(loaded.items[0].paths, ["incoming/file_0.png"])
        finally:
            os.unlink(path)

    def test_fan_out_even_split(self):
        manifest = self._make_manifest(8)
        chunks = manifest.fan_out(4)
        self.assertEqual(len(chunks), 4)
        self.assertEqual(len(chunks[0]), 2)

    def test_fan_out_uneven_split(self):
        manifest = self._make_manifest(10)
        chunks = manifest.fan_out(3)
        # ceil(10/3) = 4, so chunks are [4, 4, 2]
        self.assertEqual(len(chunks), 3)
        total = sum(len(c) for c in chunks)
        self.assertEqual(total, 10)

    def test_fan_out_single_chunk(self):
        manifest = self._make_manifest(5)
        chunks = manifest.fan_out(1)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0]), 5)

    def test_fan_out_more_chunks_than_items(self):
        manifest = self._make_manifest(3)
        chunks = manifest.fan_out(10)
        total = sum(len(c) for c in chunks)
        self.assertEqual(total, 3)

    def test_fan_out_zero_chunks(self):
        manifest = self._make_manifest(5)
        chunks = manifest.fan_out(0)
        # Should default to 1
        self.assertEqual(len(chunks), 1)

    def test_generate_batch_id(self):
        batch_id = Manifest.generate_batch_id()
        self.assertTrue(batch_id.startswith("batch-"))


if __name__ == "__main__":
    unittest.main()
