"""
tests/unit-tests/test_email_credentials.py — issue #443, session 1.

Uses `keyring`'s in-memory testing backend so these tests don't touch the
real OS credential store and pass identically in CI (headless Linux) and
on a developer machine.
"""

from __future__ import annotations

import keyring
import pytest

from opensak.email import credentials


@pytest.fixture(autouse=True)
def _in_memory_keyring(monkeypatch):
    """Swap the real OS keyring backend for a simple in-memory fake."""
    store: dict[tuple[str, str], str] = {}

    class _FakeKeyring:
        def get_password(self, service, username):
            return store.get((service, username))

        def set_password(self, service, username, password):
            store[(service, username)] = password

        def delete_password(self, service, username):
            from keyring.errors import PasswordDeleteError
            if (service, username) not in store:
                raise PasswordDeleteError("not found")
            del store[(service, username)]

    fake = _FakeKeyring()
    monkeypatch.setattr(keyring, "get_password", fake.get_password)
    monkeypatch.setattr(keyring, "set_password", fake.set_password)
    monkeypatch.setattr(keyring, "delete_password", fake.delete_password)
    yield store


def test_save_and_load_password():
    credentials.save_password("alice@gmail.com", "hunter2")
    assert credentials.load_password("alice@gmail.com") == "hunter2"


def test_load_password_missing_returns_none():
    assert credentials.load_password("nobody@example.com") is None


def test_load_password_empty_username_returns_none():
    assert credentials.load_password("") is None


def test_has_password():
    assert credentials.has_password("bob@icloud.com") is False
    credentials.save_password("bob@icloud.com", "swordfish")
    assert credentials.has_password("bob@icloud.com") is True


def test_save_password_overwrites_existing():
    credentials.save_password("carol@gmail.com", "first")
    credentials.save_password("carol@gmail.com", "second")
    assert credentials.load_password("carol@gmail.com") == "second"


def test_delete_password():
    credentials.save_password("dave@gmail.com", "secret")
    credentials.delete_password("dave@gmail.com")
    assert credentials.load_password("dave@gmail.com") is None


def test_delete_password_missing_does_not_raise():
    # Deleting something that was never saved must be a silent no-op —
    # callers (e.g. Settings dialog save logic) rely on this.
    credentials.delete_password("never-existed@example.com")


def test_delete_password_empty_username_does_not_raise():
    credentials.delete_password("")


def test_load_password_backend_error_returns_none(monkeypatch):
    """A broken/unavailable keyring backend (e.g. a minimal headless Linux
    box with no Secret Service) must degrade to 'no password saved'
    rather than crashing the Settings dialog."""

    def _raise(*args, **kwargs):
        raise RuntimeError("no backend available")

    monkeypatch.setattr(keyring, "get_password", _raise)
    assert credentials.load_password("someone@gmail.com") is None
