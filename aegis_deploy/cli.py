"""Aegis Deploy CLI entry point."""

import argparse
import logging
import sys

from aegis_deploy.config.config_loader import load_config

logger = logging.getLogger(__name__)


def main():
    """Main CLI dispatcher for aegis-deploy."""
    parser = argparse.ArgumentParser(
        prog="aegis-deploy",
        description="Aegis Deploy — Medical Image De-Identification Platform",
    )
    parser.add_argument(
        "--env",
        default=None,
        help="Environment name (qa, prod). Overrides AEGIS_DEPLOY_ENV.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # discover sub-command
    discover_parser = subparsers.add_parser("discover", help="Run the Discovery Operator")
    discover_parser.add_argument(
        "--output", "-o", default="manifest.json", help="Path to write the manifest JSON"
    )

    # run sub-command
    run_parser = subparsers.add_parser("run", help="Run the de-identification MAP pipeline")
    run_parser.add_argument("--manifest", "-m", required=True, help="Path to manifest JSON")
    run_parser.add_argument(
        "--chunk-index", type=int, default=None, help="Process only this chunk index (for fan-out)"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Load config with optional env override
    config = load_config(env_override=args.env)
    logger.info("Loaded config for environment: %s", config.get("environment", "default"))

    if args.command == "discover":
        from aegis_deploy.operators.discovery import DiscoveryOperator

        operator = DiscoveryOperator(config)
        manifest = operator.scan()
        manifest.save(args.output)
        logger.info("Manifest written to %s (%d items)", args.output, len(manifest.items))

    elif args.command == "run":
        from aegis_deploy.map.app import AegisDeIDApp

        app = AegisDeIDApp(config, args.manifest, chunk_index=args.chunk_index)
        app.run()


if __name__ == "__main__":
    main()
