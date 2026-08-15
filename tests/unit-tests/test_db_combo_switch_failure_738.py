# tests/unit-tests/test_db_combo_switch_failure_738.py — issue #738.
#
# _on_db_combo_changed() (toolbar database dropdown) used to call
# manager.switch_to() with no exception handling — a migration failure
# propagated uncaught through the Qt slot, indistinguishable from a hang
# in a console-less build. It now catches the failure, shows an error
# dialog, and resets the dropdown back to the still-active database
# instead of leaving it showing the failed switch as if it had gone
# through.

from unittest.mock import MagicMock, patch

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

    db_path = tmp_path / "test_db_combo_738.db"
    init_db(db_path=db_path)
    monkeypatch.setattr(mgr_module, "_manager", make_fake_manager(db_path, name="ComboSwitchTest"))

    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)

    yield win

    win.close()
    mgr_module._manager = None


class TestDbComboSwitchFailure:
    def test_failed_switch_shows_critical_error_not_a_silent_hang(self, window, monkeypatch):
        import opensak.db.manager as mgr_module

        fake_target = MagicMock(name="fake_target_db")
        fake_target.name = "Other DB"

        manager = mgr_module.get_db_manager()
        monkeypatch.setattr(manager, "switch_to", MagicMock(side_effect=RuntimeError("simulated migration failure")))
        monkeypatch.setattr(window, "_db_combo", MagicMock())
        window._db_combo.itemData.return_value = fake_target

        crit = MagicMock()
        with patch("opensak.gui.mainwindow.QMessageBox.critical", crit):
            with patch.object(window, "_reload_db_combo") as mock_reload:
                with patch.object(window, "_on_database_switched") as mock_switched:
                    window._on_db_combo_changed(1)

        # The failure must surface as a visible error...
        crit.assert_called_once()
        # ...the dropdown must be reset rather than left showing the
        # failed switch as if it had succeeded...
        mock_reload.assert_called_once()
        # ...and the rest of the "switch completed" flow must NOT run
        # (no detail-panel clear, map reload, etc. for a switch that
        # never actually happened).
        mock_switched.assert_not_called()

    def test_successful_switch_still_works(self, window, monkeypatch):
        import opensak.db.manager as mgr_module

        fake_target = MagicMock(name="fake_target_db")
        fake_target.name = "Other DB"

        manager = mgr_module.get_db_manager()
        monkeypatch.setattr(manager, "switch_to", MagicMock())  # succeeds
        monkeypatch.setattr(window, "_db_combo", MagicMock())
        window._db_combo.itemData.return_value = fake_target

        crit = MagicMock()
        with patch("opensak.gui.mainwindow.QMessageBox.critical", crit):
            with patch.object(window, "_on_database_switched") as mock_switched:
                window._on_db_combo_changed(1)

        crit.assert_not_called()
        mock_switched.assert_called_once_with(fake_target)
