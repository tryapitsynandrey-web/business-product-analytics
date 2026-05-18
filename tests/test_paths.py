from __future__ import annotations

import utils.paths as paths


def test_ensure_directories_creates_configured_and_extra_directories(tmp_path, monkeypatch):
    configured = [tmp_path / "configured" / "data", tmp_path / "configured" / "reports"]
    extra = [tmp_path / "runtime" / "sqlite"]
    monkeypatch.setattr(paths, "PROJECT_DIRECTORIES", configured)

    paths.ensure_directories(extra)

    for directory in configured + extra:
        assert directory.is_dir()


def test_ensure_directories_accepts_no_extra_directories(tmp_path, monkeypatch):
    configured = [tmp_path / "configured" / "only"]
    monkeypatch.setattr(paths, "PROJECT_DIRECTORIES", configured)

    paths.ensure_directories()

    assert configured[0].is_dir()
