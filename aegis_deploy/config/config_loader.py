"""Configuration loader with environment variable interpolation and overlay merging.

Follows the same ${VAR_NAME:default} pattern used in the aegis core library,
ensuring consistency between the core pipeline config and the deploy wrapper config.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}^{]+)\}")


def _interpolate_env_vars(value: str) -> str:
    """Replace ${VAR_NAME:default} patterns with environment variable values.

    If the environment variable is not set, the default value (after the colon)
    is used. If no default is provided and the variable is unset, the raw
    placeholder is left in place and a warning is logged.
    """

    def _replace(match: re.Match) -> str:
        expr = match.group(1)
        if ":" in expr:
            var_name, default = expr.split(":", 1)
        else:
            var_name, default = expr, None

        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        if default is not None:
            return default

        logger.warning("Environment variable '%s' is not set and has no default", var_name)
        return match.group(0)

    return _ENV_VAR_PATTERN.sub(_replace, value)


def _deep_interpolate(obj: Any) -> Any:
    """Recursively interpolate environment variables in a nested dict/list."""
    if isinstance(obj, str):
        return _interpolate_env_vars(obj)
    if isinstance(obj, dict):
        return {k: _deep_interpolate(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_interpolate(item) for item in obj]
    return obj


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep-merge overlay into base dict. Overlay values take precedence."""
    merged = base.copy()
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict:
    """Load and parse a YAML file."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data if data is not None else {}


def load_config(env_override: str | None = None) -> dict:
    """Load configuration by merging base.yaml with the environment overlay.

    Resolution order:
    1. Load ``config/base.yaml``
    2. Determine environment from ``env_override`` arg or ``AEGIS_DEPLOY_ENV``
       env var (defaults to ``qa``)
    3. Merge environment overlay (e.g. ``config/qa.yaml``) on top of base
    4. Interpolate ``${VAR:default}`` placeholders from environment variables

    Args:
        env_override: Explicit environment name. Takes priority over the
            ``AEGIS_DEPLOY_ENV`` environment variable.

    Returns:
        Fully resolved configuration dictionary.

    Raises:
        FileNotFoundError: If base.yaml or the overlay file does not exist.
    """
    # 1. Load base config
    base_path = _CONFIG_DIR / "base.yaml"
    if not base_path.exists():
        raise FileNotFoundError(f"Base config not found: {base_path}")
    config = _load_yaml(base_path)

    # 2. Determine environment
    env_name = env_override or os.environ.get("AEGIS_DEPLOY_ENV", "qa")
    config["environment"] = env_name

    # 3. Merge overlay
    overlay_path = _CONFIG_DIR / f"{env_name}.yaml"
    if overlay_path.exists():
        overlay = _load_yaml(overlay_path)
        config = _deep_merge(config, overlay)
        logger.info("Merged overlay: %s", overlay_path.name)
    else:
        logger.warning("No overlay file found for env '%s' at %s", env_name, overlay_path)

    # 4. Interpolate env vars
    config = _deep_interpolate(config)

    return config
