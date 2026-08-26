"""
Unit tests for explorer/utils/updater.py's PLUGINS.md-compliant HTTP conventions
(new_session() + a User-Agent blended with EDMC's own, not a bespoke string).

Run with:
    .venv/bin/python -m pytest tests/test_updater.py -v --tb=short
"""
import pytest
from typing import Generator

import tests.edmc.requests as mock_requests
from explorer.utils.updater import Notices, Updater, read_version_file

@pytest.fixture(autouse=True)
def clear_mock_calls() -> Generator[None, None, None]:
    """ Also forces mock mode -- _use_live is a global a
    prior harness test may have left True, and it never
    resets on its own. """
    previous:bool = mock_requests.live_requests()
    mock_requests.live_requests(False)
    yield
    mock_requests.live_requests(previous)

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

class TestNotices:
    """ Cursory integration check -- Notices' parsing and
    dismissal logic is exhaustively covered by EDMC-PluginLib's
    tests/test_notices.py; this just confirms fetch, parse, and
    dismiss-then-newer-shows-again round-trip in this plugin's
    own stack. """

    def test_fetch_parse_and_dismiss_round_trip(self) -> None:
        mock_requests.queue_response("get", mock_requests.MockResponse(
            status_code=200, content="## 3\nFleet Carrier routes now track tritium separately from cargo."))
        notices = Notices("dwomble", "EDMC-ExplorerLite-NoticesTest")
        notices._check_notices()
        assert notices.pending_notice == "Fleet Carrier routes now track tritium separately from cargo."

        notices.dismiss_notice()
        assert notices.pending_notice is None

        mock_requests.queue_response("get", mock_requests.MockResponse(status_code=200, content="## 4\nA newer notice."))
        notices._check_notices()
        assert notices.pending_notice == "A newer notice."

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
