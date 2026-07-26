# tests/e2e-tests/test_e2e_db_combo.py — database dropdown toolbar scenarios.

import pytest

pytest.importorskip("pytestqt")


# ── Fixtures ───────────────────────────────────────────────────────────────────


def _make_two_db_manager(db_path_a, db_path_b):
    # Fake manager with two databases; db_path_a is active.
    from opensak.db.manager import DatabaseInfo

    class _FakeTwoManager:
        def __init__(self):
            self._a = DatabaseInfo("Alpha", db_path_a)
            self._b = DatabaseInfo("Beta", db_path_b)
            self._active = self._a
            self.switch_calls = []

        @property
        def active(self):
            return self._active

        @property
        def active_path(self):
            return self._active.path

        @property
        def databases(self):
            return [self._a, self._b]

        def ensure_active_initialised(self):
            pass

        def switch_to(self, db_info):
            self.switch_calls.append(db_info)
            self._active = db_info

        def new_database(self, _name, path=None):
            raise RuntimeError("new_database called during e2e test")

    return _FakeTwoManager()


@pytest.fixture
def combo_window(qtbot, tmp_path, monkeypatch):
    # MainWindow with a single-database manager.
    import opensak.db.manager as mgr_module
    from opensak.db.database import init_db
    from opensak.lang import load_language
    from tests.data import make_fake_manager

    load_language("en")

    db_path = tmp_path / "combo.db"
    init_db(db_path=db_path)
    monkeypatch.setattr(mgr_module, "_manager", make_fake_manager(db_path))

    from opensak.gui.mainwindow import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(200)

    yield window

    mgr_module._manager = None


@pytest.fixture
def two_db_combo_window(qtbot, tmp_path, monkeypatch):
    # MainWindow with a two-database manager.
    import opensak.db.manager as mgr_module
    from opensak.db.database import init_db
    from opensak.lang import load_language

    load_language("en")

    db_path_a = tmp_path / "alpha.db"
    db_path_b = tmp_path / "beta.db"
    init_db(db_path=db_path_a)

    fake_mgr = _make_two_db_manager(db_path_a, db_path_b)
    monkeypatch.setattr(mgr_module, "_manager", fake_mgr)

    from opensak.gui.mainwindow import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(200)

    yield window, fake_mgr

    mgr_module._manager = None


# ── Presence and population ───────────────────────────────────────────────────


def test_db_combo_present(combo_window, qtbot):
    # The toolbar combo widget is always created.
    assert hasattr(combo_window, "_db_combo")
    assert combo_window._db_combo is not None


def test_db_combo_shows_all_databases(combo_window, qtbot):
    # Combo contains one entry per database registered in the manager.
    assert combo_window._db_combo.count() == 1


def test_db_combo_shows_database_name(combo_window, qtbot):
    # The combo entry text matches the database name.
    assert combo_window._db_combo.itemText(0) == "E2ETest"


def test_db_combo_two_databases_shown(two_db_combo_window, qtbot):
    # Combo shows both databases when manager has two.
    window, _ = two_db_combo_window
    assert window._db_combo.count() == 2
    names = [window._db_combo.itemText(i) for i in range(window._db_combo.count())]
    assert "Alpha" in names
    assert "Beta" in names


# ── Active selection ───────────────────────────────────────────────────────────


def test_db_combo_active_database_is_selected(combo_window, qtbot):
    # The active database is pre-selected in the combo.
    assert combo_window._db_combo.currentText() == "E2ETest"


def test_db_combo_active_is_first_entry(two_db_combo_window, qtbot):
    # Alpha (the active DB) is the selected entry on startup.
    window, _ = two_db_combo_window
    assert window._db_combo.currentText() == "Alpha"


# ── Switching ─────────────────────────────────────────────────────────────────


def test_db_combo_switch_calls_manager(two_db_combo_window, qtbot):
    # Selecting a different combo entry calls manager.switch_to with that DB.
    window, fake_mgr = two_db_combo_window

    beta_index = next(
        i for i in range(window._db_combo.count())
        if window._db_combo.itemText(i) == "Beta"
    )
    window._db_combo.setCurrentIndex(beta_index)
    qtbot.wait(50)

    assert len(fake_mgr.switch_calls) == 1
    assert fake_mgr.switch_calls[0].name == "Beta"


def test_db_combo_updates_after_switch(two_db_combo_window, qtbot):
    # After switching, the combo selection reflects the new active database.
    window, fake_mgr = two_db_combo_window

    beta_index = next(
        i for i in range(window._db_combo.count())
        if window._db_combo.itemText(i) == "Beta"
    )
    window._db_combo.setCurrentIndex(beta_index)
    qtbot.wait(50)

    assert window._db_combo.currentText() == "Beta"


def test_db_combo_refreshes_on_database_switched_signal(two_db_combo_window, qtbot):
    # Calling _on_database_switched (e.g. from the dialog) refreshes the combo.
    window, fake_mgr = two_db_combo_window

    fake_mgr._active = fake_mgr._b
    window._on_database_switched(fake_mgr._b)
    qtbot.wait(50)

    assert window._db_combo.currentText() == "Beta"


# ── Column View quick-switch combo (#607 follow-up) ──────────────────────────
#
# A Facebook beta tester reported that columns switched correctly per
# database, but the toolbar Column View dropdown always showed "(None)"
# even for a database whose configuration was actually set from a saved
# view — because the combo used to unconditionally reset to "(None)"
# after every use and after every database switch. It now recomputes,
# on each populate, whether the active database's current column
# configuration matches a saved view byte-for-byte, and selects that
# view if so.

def test_column_view_combo_shows_matching_view_for_active_db(
    combo_window, qtbot, tmp_path, monkeypatch
):
    from opensak.gui.dialogs.column_dialog import (
        ColumnView, get_visible_columns, get_column_widths,
        get_container_display, get_type_display,
    )
    window = combo_window
    monkeypatch.setattr(ColumnView, "_views_dir", staticmethod(lambda: tmp_path / "column_views"))

    view = ColumnView(
        "My Standard",
        visible_columns=get_visible_columns(),
        widths=get_column_widths(),
        container_display=get_container_display(),
        type_display=get_type_display(),
    )
    view.save()

    window._populate_column_view_combo()
    qtbot.wait(50)

    assert window._column_view_combo.currentText() == "My Standard"


def test_column_view_combo_shows_none_for_non_matching_db(
    two_db_combo_window, qtbot, tmp_path, monkeypatch
):
    from opensak.gui.dialogs.column_dialog import (
        ColumnView, get_visible_columns, get_column_widths,
        get_container_display, get_type_display, set_visible_columns,
    )
    window, fake_mgr = two_db_combo_window
    monkeypatch.setattr(ColumnView, "_views_dir", staticmethod(lambda: tmp_path / "column_views"))

    # Save a view matching Alpha's (currently active) configuration.
    ColumnView(
        "Alpha's View",
        visible_columns=get_visible_columns(),
        widths=get_column_widths(),
        container_display=get_container_display(),
        type_display=get_type_display(),
    ).save()
    window._populate_column_view_combo()
    qtbot.wait(50)
    assert window._column_view_combo.currentText() == "Alpha's View"

    # Switch to Beta and give it a deliberately different, non-matching
    # column configuration.
    fake_mgr._active = fake_mgr._b
    window._on_database_switched(fake_mgr._b)
    set_visible_columns(["gc_code", "name", "difficulty"])
    window._populate_column_view_combo()
    qtbot.wait(50)

    assert window._column_view_combo.currentText() == "(None)"

    # Switching back to Alpha should show the matching view again — this
    # is a fresh comparison each time, not a value that got "stuck".
    fake_mgr._active = fake_mgr._a
    window._on_database_switched(fake_mgr._a)
    qtbot.wait(50)

    assert window._column_view_combo.currentText() == "Alpha's View"


def test_column_view_combo_reflects_view_after_applying_from_toolbar(
    combo_window, qtbot, tmp_path, monkeypatch
):
    from opensak.gui.dialogs.column_dialog import (
        ColumnView, set_visible_columns,
    )
    window = combo_window
    monkeypatch.setattr(ColumnView, "_views_dir", staticmethod(lambda: tmp_path / "column_views"))

    # Make the active database's configuration deliberately not match any
    # saved view yet.
    set_visible_columns(["gc_code", "name", "found"])
    path = ColumnView("Trip View", visible_columns=["gc_code", "name", "difficulty"]).save()
    window._populate_column_view_combo()
    qtbot.wait(50)
    assert window._column_view_combo.currentText() == "(None)"

    idx = next(
        i for i in range(window._column_view_combo.count())
        if window._column_view_combo.itemData(i) == path
    )
    window._column_view_combo.setCurrentIndex(idx)
    window._on_column_view_combo_changed(idx)
    qtbot.wait(50)

    # After applying "Trip View" from the toolbar, the combo should show
    # it as selected — the database's configuration now matches it.
    assert window._column_view_combo.currentText() == "Trip View"
