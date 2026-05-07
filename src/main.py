"""
main.py — Entry point for the ProductPulse Analytics Decision Engine.

Responsibility:
    Parse optional CLI arguments, invoke ProductAnalyticsPipeline,
    surface a concise result message, and exit with an appropriate code.

No business logic or analytics calculations live here.
"""

import argparse
import sys
from pathlib import Path

from core.pipeline import ProductAnalyticsPipeline


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="productpulse",
        description="ProductPulse — Business Product Analytics Decision Engine.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Path to a config.yaml file. "
            "Defaults to config/config.yaml relative to the project root."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """
    Run the analytics pipeline and return an exit code.

    Returns
    -------
    int
        0 on success, 1 on any failure.
    """
    args = _parse_args()

    pipeline = ProductAnalyticsPipeline(config_path=args.config)
    result = pipeline.run()

    if result.success:
        print(f"\n✓ {result.message}")
        return 0
    else:
        print(f"\n✗ {result.message}", file=sys.stderr)
        if result.issues:
            for issue in result.issues:
                print(f"  • {issue}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
