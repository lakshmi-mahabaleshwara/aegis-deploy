"""Unit tests for the configuration loader."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aegis_deploy.config.config_loader import (
    _deep_interpolate,
    _deep_merge,
    load_config,
)


class TestEnvVarInterpolation(unittest.TestCase):
    """Test ${VAR:default} interpolation."""

    def test_interpolate_with_env_var_set(self):
        with patch.dict(os.environ, {"MY_VAR": "hello"}):
            result = _deep_interpolate("${MY_VAR:fallback}")
            self.assertEqual(result, "hello")

    def test_interpolate_with_default(self):
        # Ensure the var is NOT set
        os.environ.pop("MISSING_VAR", None)
        result = _deep_interpolate("${MISSING_VAR:default_value}")
        self.assertEqual(result, "default_value")

    def test_interpolate_no_default_no_var(self):
        os.environ.pop("UNDEFINED_VAR", None)
        result = _deep_interpolate("${UNDEFINED_VAR}")
        # Should keep placeholder when no default and no env var
        self.assertEqual(result, "${UNDEFINED_VAR}")

    def test_interpolate_nested_dict(self):
        with patch.dict(os.environ, {"DB_HOST": "prod-db.example.com"}):
            data = {"vault": {"host": "${DB_HOST:localhost}", "port": "5432"}}
            result = _deep_interpolate(data)
            self.assertEqual(result["vault"]["host"], "prod-db.example.com")
            self.assertEqual(result["vault"]["port"], "5432")

    def test_interpolate_list(self):
        data = ["${MISSING:a}", "${MISSING:b}"]
        result = _deep_interpolate(data)
        self.assertEqual(result, ["a", "b"])

    def test_interpolate_non_string(self):
        self.assertEqual(_deep_interpolate(42), 42)
        self.assertEqual(_deep_interpolate(True), True)
        self.assertIsNone(_deep_interpolate(None))


class TestDeepMerge(unittest.TestCase):
    """Test deep merge of config dicts."""

    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        overlay = {"b": 3, "c": 4}
        result = _deep_merge(base, overlay)
        self.assertEqual(result, {"a": 1, "b": 3, "c": 4})

    def test_nested_merge(self):
        base = {"db": {"host": "localhost", "port": 5432}}
        overlay = {"db": {"host": "prod-db"}}
        result = _deep_merge(base, overlay)
        self.assertEqual(result["db"]["host"], "prod-db")
        self.assertEqual(result["db"]["port"], 5432)

    def test_overlay_replaces_non_dict(self):
        base = {"key": "old"}
        overlay = {"key": {"nested": True}}
        result = _deep_merge(base, overlay)
        self.assertEqual(result["key"], {"nested": True})

    def test_base_unchanged(self):
        base = {"a": 1}
        overlay = {"a": 2}
        _deep_merge(base, overlay)
        self.assertEqual(base["a"], 1)  # Original dict not mutated


class TestLoadConfig(unittest.TestCase):
    """Test full config loading flow."""

    def test_loads_base_config(self):
        config = load_config(env_override="qa")
        self.assertIn("aws", config)
        self.assertIn("storage", config)
        self.assertIn("vault", config)
        self.assertIn("aegis", config)
        self.assertEqual(config["environment"], "qa")

    def test_qa_overlay_applied(self):
        config = load_config(env_override="qa")
        # QA should have debug logging
        self.assertEqual(config["logging"]["level"], "DEBUG")

    def test_prod_overlay_applied(self):
        config = load_config(env_override="prod")
        # Prod should have INFO logging and CloudWatch enabled
        self.assertEqual(config["logging"]["level"], "INFO")
        self.assertTrue(config["monitoring"]["cloudwatch"]["enabled"])

    def test_env_var_override(self):
        with patch.dict(os.environ, {"AEGIS_DEPLOY_ENV": "prod"}):
            config = load_config()
            self.assertEqual(config["environment"], "prod")

    def test_explicit_env_takes_priority(self):
        with patch.dict(os.environ, {"AEGIS_DEPLOY_ENV": "prod"}):
            config = load_config(env_override="qa")
            self.assertEqual(config["environment"], "qa")


if __name__ == "__main__":
    unittest.main()
