from __future__ import annotations

import sys
from types import SimpleNamespace

import main as productpulse_main
from utils.paths import PROJECT_ROOT


def test_main_run_returns_zero_and_prints_outputs_on_success(monkeypatch, capsys, tmp_path):
    seen = {}

    class FakePipeline:
        def __init__(self, config_path=None):
            seen["config_path"] = config_path

        def run(self):
            return SimpleNamespace(
                success=True,
                message="pipeline ok",
                generated_outputs=["data/processed/kpi_summary.csv"],
                issues=[],
            )

    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr(sys, "argv", ["productpulse", "run", "--config", str(config_path)])
    monkeypatch.setattr(productpulse_main, "ProductAnalyticsPipeline", FakePipeline)

    assert productpulse_main.main() == 0
    assert seen["config_path"] == config_path
    captured = capsys.readouterr()
    assert "OK: pipeline ok" in captured.out
    assert "Generated 1 output artifact(s)." in captured.out


def test_main_run_success_without_outputs_skips_generated_message(monkeypatch, capsys):
    class FakePipeline:
        def __init__(self, config_path=None):
            self.config_path = config_path

        def run(self):
            return SimpleNamespace(
                success=True,
                message="pipeline ok",
                generated_outputs=[],
                issues=[],
            )

    monkeypatch.setattr(sys, "argv", ["productpulse", "run"])
    monkeypatch.setattr(productpulse_main, "ProductAnalyticsPipeline", FakePipeline)

    assert productpulse_main.main() == 0
    captured = capsys.readouterr()
    assert "OK: pipeline ok" in captured.out
    assert "Generated" not in captured.out


def test_reset_demo_removes_database_and_runs_pipeline(monkeypatch, capsys, tmp_path):
    db_path = tmp_path / "productpulse.db"
    db_path.write_text("old", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    seen = {}

    class FakePipeline:
        def __init__(self, config_path=None):
            seen["config_path"] = config_path
            self._sqlite_path = str(db_path)

        def run(self):
            seen["ran"] = True
            return SimpleNamespace(
                success=True,
                message="pipeline ok",
                generated_outputs=["data/local/productpulse.db"],
                issues=[],
            )

    monkeypatch.setattr(sys, "argv", ["productpulse", "reset-demo", "--config", str(config_path)])
    monkeypatch.setattr(productpulse_main, "ProductAnalyticsPipeline", FakePipeline)

    assert productpulse_main.main() == 0
    assert seen == {"config_path": config_path, "ran": True}
    assert not db_path.exists()
    captured = capsys.readouterr()
    assert "Removed local SQLite demo database" in captured.out
    assert "Regenerating deterministic demo snapshot" in captured.out
    assert "Generated 1 output artifact(s)." in captured.out


def test_reset_demo_runs_pipeline_when_database_is_missing(monkeypatch, capsys, tmp_path):
    db_path = tmp_path / "productpulse.db"
    seen = {}

    class FakePipeline:
        def __init__(self, config_path=None):
            seen["config_path"] = config_path
            self._sqlite_path = str(db_path)

        def run(self):
            seen["ran"] = True
            return SimpleNamespace(
                success=True,
                message="pipeline ok",
                generated_outputs=[],
                issues=[],
            )

    monkeypatch.setattr(sys, "argv", ["productpulse", "reset-demo"])
    monkeypatch.setattr(productpulse_main, "ProductAnalyticsPipeline", FakePipeline)

    assert productpulse_main.main() == 0
    assert seen == {"config_path": None, "ran": True}
    captured = capsys.readouterr()
    assert "No local SQLite demo database found" in captured.out
    assert "OK: pipeline ok" in captured.out


def test_main_run_returns_one_and_prints_issues_on_failure(monkeypatch, capsys):
    class FakePipeline:
        def __init__(self, config_path=None):
            self.config_path = config_path

        def run(self):
            return SimpleNamespace(
                success=False,
                message="validation failed",
                generated_outputs=[],
                issues=["customers missing customer_id"],
            )

    monkeypatch.setattr(sys, "argv", ["productpulse"])
    monkeypatch.setattr(productpulse_main, "ProductAnalyticsPipeline", FakePipeline)

    assert productpulse_main.main() == 1
    captured = capsys.readouterr()
    assert "ERROR: validation failed" in captured.err
    assert "customers missing customer_id" in captured.err


def test_main_run_failure_without_issues_skips_issue_lines(monkeypatch, capsys):
    class FakePipeline:
        def __init__(self, config_path=None):
            self.config_path = config_path

        def run(self):
            return SimpleNamespace(
                success=False,
                message="failed",
                generated_outputs=[],
                issues=[],
            )

    monkeypatch.setattr(sys, "argv", ["productpulse", "run"])
    monkeypatch.setattr(productpulse_main, "ProductAnalyticsPipeline", FakePipeline)

    assert productpulse_main.main() == 1
    captured = capsys.readouterr()
    assert "ERROR: failed" in captured.err
    assert "  -" not in captured.err


def test_status_returns_one_when_database_is_missing(monkeypatch, capsys, tmp_path):
    missing_db = tmp_path / "missing.db"

    class FakePipeline:
        def __init__(self, config_path=None):
            self.config_path = config_path
            self.config = {"project": {"name": "TestPulse"}}
            self._sqlite_path = str(missing_db)
            self._sqlite_enabled = True

    monkeypatch.setattr(sys, "argv", ["productpulse", "status"])
    monkeypatch.setattr(productpulse_main, "ProductAnalyticsPipeline", FakePipeline)

    assert productpulse_main.main() == 1
    captured = capsys.readouterr()
    assert "Project: TestPulse" in captured.out
    assert "database missing" in captured.out


def test_status_prints_table_counts_when_database_is_ready(monkeypatch, capsys, tmp_path):
    db_path = tmp_path / "productpulse.db"
    db_path.write_text("", encoding="utf-8")

    class FakePipeline:
        def __init__(self, config_path=None):
            self.config_path = config_path
            self.config = {"project": {"name": "TestPulse"}}
            self._sqlite_path = str(db_path)
            self._sqlite_enabled = True

    class FakeReader:
        def __init__(self, path):
            assert path == db_path

        def list_tables(self):
            return ["kpi_summary", "health_scores"]

        def get_table_row_count(self, table):
            return {"kpi_summary": 3, "health_scores": 2}[table]

    monkeypatch.setattr(sys, "argv", ["productpulse", "status"])
    monkeypatch.setattr(productpulse_main, "ProductAnalyticsPipeline", FakePipeline)
    monkeypatch.setattr(productpulse_main, "SQLiteReader", FakeReader)

    assert productpulse_main.main() == 0
    captured = capsys.readouterr()
    assert "database ready (2 table(s))" in captured.out
    assert "- kpi_summary: 3 row(s)" in captured.out
    assert "- health_scores: 2 row(s)" in captured.out


def test_status_prints_unavailable_when_row_count_fails(monkeypatch, capsys, tmp_path):
    db_path = tmp_path / "productpulse.db"
    db_path.write_text("", encoding="utf-8")

    class FakePipeline:
        def __init__(self, config_path=None):
            self.config_path = config_path
            self.config = {"project": {"name": "TestPulse"}}
            self._sqlite_path = str(db_path)
            self._sqlite_enabled = True

    class FakeReader:
        def __init__(self, path):
            assert path == db_path

        def list_tables(self):
            return ["kpi_summary"]

        def get_table_row_count(self, table):
            raise ValueError("bad table")

    monkeypatch.setattr(sys, "argv", ["productpulse", "status"])
    monkeypatch.setattr(productpulse_main, "ProductAnalyticsPipeline", FakePipeline)
    monkeypatch.setattr(productpulse_main, "SQLiteReader", FakeReader)

    assert productpulse_main.main() == 0
    captured = capsys.readouterr()
    assert "- kpi_summary: row count unavailable" in captured.out


def test_dashboard_launch_uses_streamlit_and_project_pythonpath(monkeypatch):
    captured = {}

    def fake_call(cmd, cwd, env):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["env"] = env
        return 7

    monkeypatch.setattr(sys, "argv", ["productpulse", "dashboard"])
    monkeypatch.setattr(productpulse_main.subprocess, "call", fake_call)

    assert productpulse_main.main() == 7
    assert captured["cmd"] == [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app/streamlit_app.py",
    ]
    assert captured["cwd"] == PROJECT_ROOT
    assert str(PROJECT_ROOT / "src") in captured["env"]["PYTHONPATH"]
