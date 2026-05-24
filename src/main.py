"""
main.py - Entry point for the ProductPulse Analytics Decision Engine.

Responsibility:
    Parse optional CLI arguments, invoke ProductAnalyticsPipeline,
    surface a concise result message, and exit with an appropriate code.

No business logic or analytics calculations live here.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from core.pipeline import ProductAnalyticsPipeline
from adapters.sqlite_reader import SQLiteReader
from utils.paths import PROJECT_ROOT


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="productpulse",
        description="ProductPulse - Business Product Analytics Decision Engine.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=("run", "status", "dashboard", "reset-demo"),
        help="Command to execute. Defaults to 'run'.",
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


def _execute_pipeline(pipeline: ProductAnalyticsPipeline) -> int:
    result = pipeline.run()

    if result.success:
        print(f"\nOK: {result.message}")
        if result.generated_outputs:
            print(f"Generated {len(result.generated_outputs)} output artifact(s).")
        return 0

    print(f"\nERROR: {result.message}", file=sys.stderr)
    if result.issues:
        for issue in result.issues:
            print(f"  - {issue}", file=sys.stderr)
    return 1


def _run_pipeline(config_path: Path | None) -> int:
    pipeline = ProductAnalyticsPipeline(config_path=config_path)
    return _execute_pipeline(pipeline)


def _reset_demo(config_path: Path | None) -> int:
    pipeline = ProductAnalyticsPipeline(config_path=config_path)
    db_path = Path(pipeline._sqlite_path)

    if db_path.exists():
        db_path.unlink()
        print(f"Removed local SQLite demo database: {db_path}")
    else:
        print(f"No local SQLite demo database found: {db_path}")

    print("Regenerating deterministic demo snapshot...")
    return _execute_pipeline(pipeline)


def _show_status(config_path: Path | None) -> int:
    pipeline = ProductAnalyticsPipeline(config_path=config_path)
    db_path = Path(pipeline._sqlite_path)

    print(f"Project: {pipeline.config.get('project', {}).get('name', 'ProductPulse')}")
    print(f"SQLite: {db_path}")
    print(f"SQLite enabled: {pipeline._sqlite_enabled}")

    if not db_path.exists():
        print("Status: database missing. Run `productpulse run` first.")
        return 1

    reader = SQLiteReader(db_path)
    tables = reader.list_tables()
    print(f"Status: database ready ({len(tables)} table(s))")
    for table in tables:
        try:
            print(f"- {table}: {reader.get_table_row_count(table)} row(s)")
        except ValueError:
            print(f"- {table}: row count unavailable")
    return 0


def _launch_dashboard() -> int:
    env = os.environ.copy()
    pythonpath = str(PROJECT_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{pythonpath}{os.pathsep}{existing}" if existing else pythonpath
    cmd = [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py"]
    return subprocess.call(cmd, cwd=PROJECT_ROOT, env=env)


def main() -> int:
    """
    Run the analytics pipeline and return an exit code.

    Returns
    -------
    int
        0 on success, 1 on any failure.
    """
    args = _parse_args()

    if args.command == "status":
        return _show_status(args.config)
    if args.command == "dashboard":
        return _launch_dashboard()
    if args.command == "reset-demo":
        return _reset_demo(args.config)
    return _run_pipeline(args.config)


if __name__ == "__main__":
    sys.exit(main())
