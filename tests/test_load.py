"""
Unit test for load.py's VERSION: resolved from a "version" file (the same
file CI's release.yml stamps and Updater.install() writes) rather than a
hardcoded string, and exposed as load.VERSION for plugin-browser tooling.

Run with:
    .venv/bin/python -m pytest tests/test_load.py -v --tb=short
"""
import pytest

import load
from harness import TestHarness

def test_plugin_start3_resolves_version_from_the_version_file(harness:TestHarness, tmp_path, monkeypatch) -> None:
    import explorer.db.store as store_module
    monkeypatch.setattr(store_module, "resolve_db_path", lambda: tmp_path / "explorer.sqlite")

    (tmp_path / "version").write_text("9.9.9")
    try:
        load.plugin_start3(str(tmp_path))

        assert load.VERSION == "9.9.9"
    finally:
        # session-global state -- mustn't leak into later tests
        load.plugin_start3(str(harness.plugin_dir))

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
