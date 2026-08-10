# tests/unit-tests/test_email_settings.py — AppSettings.email_pq_* (issue #443).

import pytest

pytest.importorskip("pytestqt")

from opensak.gui.settings import AppSettings
from opensak.email.get_pq.connection import DEFAULT_IMAP_PORT


@pytest.fixture
def s(tmp_path, monkeypatch):
    """Isolated AppSettings — SettingsStore backed by a temp opensak.json."""
    from opensak import settings_store
    fresh_store = settings_store.SettingsStore()
    fresh_store._data = {}
    fresh_store._path = tmp_path / "opensak.json"
    monkeypatch.setattr(settings_store, "_store", fresh_store)
    return AppSettings()


def test_defaults(s):
    assert s.email_pq_server == ""
    assert s.email_pq_port == DEFAULT_IMAP_PORT
    assert s.email_pq_username == ""


def test_set_and_get(s):
    s.email_pq_server = "imap.gmail.com"
    s.email_pq_port = 993
    s.email_pq_username = "someone@gmail.com"
    assert s.email_pq_server == "imap.gmail.com"
    assert s.email_pq_port == 993
    assert s.email_pq_username == "someone@gmail.com"


def test_server_stripped(s):
    s.email_pq_server = "  imap.gmail.com  "
    assert s.email_pq_server == "imap.gmail.com"


def test_username_stripped(s):
    s.email_pq_username = "  someone@gmail.com  "
    assert s.email_pq_username == "someone@gmail.com"


def test_port_survives_string_from_disk(s, monkeypatch):
    # settings_store persists via JSON — simulate a value coming back as
    # a string (shouldn't normally happen, but be defensive).
    s.email_pq_server  # touch to ensure store initialised
    from opensak.settings_store import get_store
    get_store().set("email_pq.port", "587")
    assert s.email_pq_port == 587


def test_port_falls_back_to_default_on_garbage(s):
    from opensak.settings_store import get_store
    get_store().set("email_pq.port", "not-a-number")
    assert s.email_pq_port == DEFAULT_IMAP_PORT
