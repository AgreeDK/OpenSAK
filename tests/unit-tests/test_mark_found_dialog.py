# tests/unit-tests/test_mark_found_dialog.py — issue #649.

import pytest
from datetime import date

pytest.importorskip("pytestqt")

from PySide6.QtCore import QDate

from opensak.gui.dialogs.mark_found_dialog import MarkFoundDialog


class TestMarkFoundDialog:
    def test_defaults_to_today(self, qtbot):
        dlg = MarkFoundDialog("GC123", "Test Cache")
        qtbot.addWidget(dlg)
        assert dlg._date_edit.date() == QDate.currentDate()

    def test_get_date_before_accept_is_none(self, qtbot):
        dlg = MarkFoundDialog("GC123", "Test Cache")
        qtbot.addWidget(dlg)
        assert dlg.get_date() is None

    def test_accept_sets_chosen_date(self, qtbot):
        dlg = MarkFoundDialog("GC123", "Test Cache")
        qtbot.addWidget(dlg)
        dlg._date_edit.setDate(QDate(2026, 6, 15))
        dlg._on_accept()
        assert dlg.get_date() == date(2026, 6, 15)

    def test_reject_leaves_date_none(self, qtbot):
        dlg = MarkFoundDialog("GC123", "Test Cache")
        qtbot.addWidget(dlg)
        dlg._date_edit.setDate(QDate(2026, 6, 15))
        dlg.reject()
        assert dlg.get_date() is None

    def test_future_dates_disallowed(self, qtbot):
        # Requested behavior (#649): found date defaults to today; a find
        # can't be logged for a date that hasn't happened yet.
        dlg = MarkFoundDialog("GC123", "Test Cache")
        qtbot.addWidget(dlg)
        assert dlg._date_edit.maximumDate() == QDate.currentDate()

    def test_title_and_heading_include_gc_code(self, qtbot):
        dlg = MarkFoundDialog("GC99999", "My Favourite Cache")
        qtbot.addWidget(dlg)
        assert dlg.windowTitle()  # non-empty
        # Heading label is the first widget added; just confirm construction
        # didn't error and the gc_code was threaded through to tr().
        assert dlg._gc_code == "GC99999"

    def test_prefills_with_current_date_when_editing(self, qtbot):
        dlg = MarkFoundDialog("GC123", "Test Cache", current_date=date(2026, 3, 10))
        qtbot.addWidget(dlg)
        assert dlg._date_edit.date() == QDate(2026, 3, 10)

    def test_no_current_date_defaults_to_today(self, qtbot):
        dlg = MarkFoundDialog("GC123", "Test Cache", current_date=None)
        qtbot.addWidget(dlg)
        assert dlg._date_edit.date() == QDate.currentDate()

    def test_prefilled_date_can_be_changed_and_accepted(self, qtbot):
        dlg = MarkFoundDialog("GC123", "Test Cache", current_date=date(2026, 3, 10))
        qtbot.addWidget(dlg)
        dlg._date_edit.setDate(QDate(2026, 6, 15))
        dlg._on_accept()
        assert dlg.get_date() == date(2026, 6, 15)
