"""Unit tests for the Identity Vault repository."""

import unittest

from aegis_deploy.vault.models import Base
from aegis_deploy.vault.repository import VaultRepository


class TestVaultRepository(unittest.TestCase):
    """Test VaultRepository CRUD using in-memory SQLite."""

    def setUp(self):
        """Create a fresh in-memory vault for each test."""
        self.config = {"host": ":memory:"}
        self.repo = VaultRepository(self.config)
        self.repo.initialize_schema()

    def test_store_and_lookup(self):
        self.repo.store_mapping(
            original_id="patient/study/001.dcm",
            deid_token="TOKEN_abcdef12",
            modality="CT",
            batch_id="batch-001",
        )
        token = self.repo.lookup_token("patient/study/001.dcm")
        self.assertEqual(token, "TOKEN_abcdef12")

    def test_lookup_missing(self):
        token = self.repo.lookup_token("nonexistent")
        self.assertIsNone(token)

    def test_idempotent_store(self):
        """Storing the same original_id twice should return the existing mapping."""
        m1 = self.repo.store_mapping(
            original_id="patient/scan.dcm",
            deid_token="TOKEN_111",
            batch_id="batch-001",
        )
        m2 = self.repo.store_mapping(
            original_id="patient/scan.dcm",
            deid_token="TOKEN_111",
            batch_id="batch-002",
        )
        self.assertEqual(m1.deid_token, m2.deid_token)
        # Should still only have one mapping
        self.assertEqual(self.repo.get_mapping_count(), 1)

    def test_get_processed_ids(self):
        self.repo.store_mapping("a.dcm", "TOKEN_a", batch_id="b1")
        self.repo.store_mapping("b.dcm", "TOKEN_b", batch_id="b1")
        self.repo.store_mapping("c.dcm", "TOKEN_c", batch_id="b2")

        processed = self.repo.get_processed_ids()
        self.assertEqual(processed, {"a.dcm", "b.dcm", "c.dcm"})

    def test_mapping_count(self):
        self.assertEqual(self.repo.get_mapping_count(), 0)
        self.repo.store_mapping("x.dcm", "TOKEN_x", batch_id="b1")
        self.assertEqual(self.repo.get_mapping_count(), 1)

    def test_multiple_modalities(self):
        self.repo.store_mapping("ct.dcm", "T1", modality="CT", batch_id="b1")
        self.repo.store_mapping("mr.dcm", "T2", modality="MR", batch_id="b1")
        self.repo.store_mapping("us.jpg", "T3", modality="US", source_type="s3", batch_id="b1")
        self.assertEqual(self.repo.get_mapping_count(), 3)


if __name__ == "__main__":
    unittest.main()
