# tests/unit-tests/test_dialog_widgets.py — delte dialog-widgets (DirRow, clamp_dialog_height_to_screen).

from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("pytestqt")

from opensak.gui.dialogs import widgets as w


class TestDirRowBrowse:
    def test_browse_normalizes_qt_forward_slashes(self, qtbot, tmp_path, monkeypatch):
        """
        Issue #609: QFileDialog.getExistingDirectory() always returns paths
        using forward slashes, regardless of platform. The displayed path
        must be normalized to the platform's native separator instead of
        showing the raw Qt-style path to the user.
        """
        row = w.DirRow(tmp_path)
        qtbot.addWidget(row)

        chosen = str(tmp_path).replace("\\", "/") + "/subdir"
        monkeypatch.setattr(
            w.QFileDialog, "getExistingDirectory", lambda *a, **k: chosen
        )

        row._browse()

        # Displayed text must go through Path() normalization rather than
        # showing Qt's raw forward-slash path verbatim — on Windows this
        # turns "E:/Users/.../subdir" into "E:\Users\...\subdir".
        assert row._edit.text() == str(Path(chosen))

    def test_browse_cancelled_leaves_text_unchanged(self, qtbot, tmp_path, monkeypatch):
        row = w.DirRow(tmp_path)
        qtbot.addWidget(row)
        original = row._edit.text()

        monkeypatch.setattr(w.QFileDialog, "getExistingDirectory", lambda *a, **k: "")

        row._browse()

        assert row._edit.text() == original

    def test_path_property_reflects_edit_text(self, qtbot, tmp_path):
        row = w.DirRow(tmp_path)
        qtbot.addWidget(row)
        assert row.path == tmp_path

    def test_set_path_updates_display(self, qtbot, tmp_path):
        row = w.DirRow(tmp_path)
        qtbot.addWidget(row)
        other = tmp_path / "elsewhere"
        row.set_path(other)
        assert row._edit.text() == str(other)


class TestClampDialogHeightToScreen:
    """
    Issue #811: Settings dialog exceeded the screen's available height at
    200% DPI scaling on a high-resolution display, cutting off content
    with no way to reach it. clamp_dialog_height_to_screen() is the
    shared fix — these tests cover its own logic in isolation (mocked
    screen/dialog, no real Qt window needed), separate from the
    per-dialog integration covered in each dialog's own test file.
    """

    def _mock_screen(self, available_height: int) -> MagicMock:
        rect = MagicMock()
        rect.height.return_value = available_height
        screen = MagicMock()
        screen.availableGeometry.return_value = rect
        return screen

    def test_caps_to_fraction_of_parents_screen(self):
        parent = MagicMock()
        parent.screen.return_value = self._mock_screen(800)
        dialog = MagicMock()

        w.clamp_dialog_height_to_screen(dialog, parent, max_fraction=0.9)

        dialog.setMaximumHeight.assert_called_once_with(720)

    def test_default_fraction_is_90_percent(self):
        parent = MagicMock()
        parent.screen.return_value = self._mock_screen(1000)
        dialog = MagicMock()

        w.clamp_dialog_height_to_screen(dialog, parent)

        dialog.setMaximumHeight.assert_called_once_with(900)

    def test_falls_back_to_primary_screen_when_parent_screen_is_none(self, monkeypatch):
        parent = MagicMock()
        parent.screen.return_value = None
        dialog = MagicMock()

        primary = self._mock_screen(800)
        monkeypatch.setattr(w.QApplication, "primaryScreen", staticmethod(lambda: primary))

        w.clamp_dialog_height_to_screen(dialog, parent)

        dialog.setMaximumHeight.assert_called_once_with(720)

    def test_falls_back_to_primary_screen_when_no_parent(self, monkeypatch):
        dialog = MagicMock()

        primary = self._mock_screen(800)
        monkeypatch.setattr(w.QApplication, "primaryScreen", staticmethod(lambda: primary))

        w.clamp_dialog_height_to_screen(dialog, parent=None)

        dialog.setMaximumHeight.assert_called_once_with(720)

    def test_does_nothing_if_no_screen_available_anywhere(self, monkeypatch):
        # Extremely unlikely in practice, but must not crash — a dialog
        # with no cap is no worse than before this fix existed.
        parent = MagicMock()
        parent.screen.return_value = None
        dialog = MagicMock()

        monkeypatch.setattr(w.QApplication, "primaryScreen", staticmethod(lambda: None))

        w.clamp_dialog_height_to_screen(dialog, parent)

        dialog.setMaximumHeight.assert_not_called()

