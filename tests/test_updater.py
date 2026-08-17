"""
Unit tests for explorer/utils/updater.py's PLUGINS.md-compliant HTTP conventions
(new_session() + a User-Agent blended with EDMC's own, not a bespoke string).

Run with:
    .venv/bin/python -m pytest tests/test_updater.py -v --tb=short
"""
import pytest
from typing import Generator

import tests.edmc.requests as mock_requests
from explorer.utils.updater import Updater, read_version_file

@pytest.fixture(autouse=True)
def clear_mock_calls() -> Generator[None, None, None]:
    mock_requests._mock_requests.calls.clear()
    yield
    mock_requests._mock_requests.calls.clear()

class TestUpdaterUserAgent:

    def test_get_release_sends_edmc_user_agent_plus_project_name(self, tmp_path) -> None:
        updater = Updater(str(tmp_path), "dwomble", "EDMC-ExplorerLite")
        mock_requests.queue_response("get", mock_requests.MockResponse(status_code=404))

        updater.get_release()

        call = mock_requests._mock_requests.calls[-1]
        assert call['headers']['User-Agent'] == "EDMC-TestHarness/1.0 EDMC-ExplorerLite-Updater"

    def test_download_zip_sends_edmc_user_agent_plus_project_name(self, tmp_path) -> None:
        updater = Updater(str(tmp_path), "dwomble", "EDMC-ExplorerLite")
        updater.update_version = "1.2.3" # type: ignore -- str is fine, only used for a filename here
        updater.download_url = "https://example.invalid/release.zip"
        mock_requests.queue_response("get", mock_requests.MockResponse(status_code=404))

        updater.download_zip()

        call = mock_requests._mock_requests.calls[-1]
        assert call['headers']['User-Agent'] == "EDMC-TestHarness/1.0 EDMC-ExplorerLite-Updater"

class TestReadVersionFile:

    def test_reads_the_version_file_when_present(self, tmp_path) -> None:
        (tmp_path / "version").write_text("1.2.3")
        assert str(read_version_file(str(tmp_path), "0.0.0-dev")) == "1.2.3"

    def test_falls_back_to_default_when_no_file_exists(self, tmp_path) -> None:
        assert str(read_version_file(str(tmp_path), "0.1.0-dev")) == "0.1.0-dev"

    def test_falls_back_to_default_when_the_file_is_unparseable(self, tmp_path) -> None:
        """ e.g. a fresh git checkout with an empty/placeholder version file. """
        (tmp_path / "version").write_text("not-a-version!!")
        assert str(read_version_file(str(tmp_path), "0.1.0-dev")) == "0.1.0-dev"

    def test_strips_surrounding_whitespace(self, tmp_path) -> None:
        """ CI's release.yml writes the tag via `echo`, which appends a newline. """
        (tmp_path / "version").write_text("1.2.3\n")
        assert str(read_version_file(str(tmp_path), "0.0.0-dev")) == "1.2.3"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
