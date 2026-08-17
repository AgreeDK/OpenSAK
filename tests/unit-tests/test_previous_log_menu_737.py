# tests/unit-tests/test_previous_log_menu_737.py — issue #737.
#
# _open_previous_log_file() opens opensak.log.previous (preserved by
# logger.setup_logging()'s rotation) via the same pattern as the existing
# "Open log file" action — shows a "not found" message if it doesn't
# exist yet (e.g. very first session ever), otherwise hands it to
# QDesktopServices like the current-session log action does.

from unittest.mock import patch

import pytest

pytest.importorskip("pytestqt")

from opensak.gui.mainwindow import MainWindow


@pytest.fixture(autouse=True)
def _quiet_startup(monkeypatch):
    monkeypatch.setattr(MainWindow, "_initial_load", lambda self: None)
    monkeypatch.setattr(MainWindow, "_check_update_background", lambda self: None)
    monkeypatch.setattr(MainWindow, "_check_setup_complete", lambda self: None)


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    import opensak.db.manager as mgr_module
    from opensak.db.database import init_db
    from opensak.lang import load_language
    from tests.data import make_fake_manager

    load_language("en")

    db_path = tmp_path / "test_previous_log_737.db"
    init_db(db_path=db_path)
    monkeypatch.setattr(mgr_module, "_manager", make_fake_manager(db_path, name="PrevLogTest"))

    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)

    yield win

    win.close()
    mgr_module._manager = None


class TestOpenPreviousLogFile:
    def test_shows_not_found_message_when_no_previous_session_yet(self, window, tmp_path):
        with patch("opensak.config.get_previous_log_path", return_value=tmp_path / "opensak.log.previous"):
            with patch("opensak.gui.mainwindow.QMessageBox.information") as mock_box:
                window._open_previous_log_file()
        assert mock_box.called

    def test_opens_file_when_previous_log_exists(self, window, tmp_path):
        prev = tmp_path / "opensak.log.previous"
        prev.write_text("some previous session content", encoding="utf-8")
        with patch("opensak.config.get_previous_log_path", return_value=prev):
            with patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
                window._open_previous_log_file()
        assert mock_open.called

    def test_does_not_touch_current_session_log_action(self, window, tmp_path):
        # Sanity check the two actions stay independent — opening the
        # previous log must not affect/require the current log's state.
        prev = tmp_path / "opensak.log.previous"
        prev.write_text("previous", encoding="utf-8")
        with patch("opensak.config.get_previous_log_path", return_value=prev):
            with patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
                window._open_previous_log_file()
        args = mock_open.call_args[0]
        assert "opensak.log.previous" in args[0].toLocalFile()
