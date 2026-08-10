"""
tests/unit-tests/test_email_get_pq_connection.py — issue #443, session 1.

All tests mock `imaplib.IMAP4_SSL` — no real network calls.
"""

from __future__ import annotations

import imaplib
import socket

import pytest

from opensak.email.get_pq.connection import (
    DEFAULT_IMAP_PORT,
    check_connection,
)


class _FakeImapOk:
    def __init__(self, *args, **kwargs):
        pass

    def login(self, username, password):
        return "OK", [b"Logged in"]

    def logout(self):
        return "BYE", [b"bye"]


class _FakeImapAuthFail:
    def __init__(self, *args, **kwargs):
        pass

    def login(self, username, password):
        raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials")

    def logout(self):
        return "BYE", [b"bye"]


def test_successful_login(monkeypatch):
    monkeypatch.setattr(imaplib, "IMAP4_SSL", _FakeImapOk)
    result = check_connection("imap.gmail.com", DEFAULT_IMAP_PORT, "a@gmail.com", "app-pw")
    assert result.success is True
    assert result.kind == "success"


def test_auth_failure(monkeypatch):
    monkeypatch.setattr(imaplib, "IMAP4_SSL", _FakeImapAuthFail)
    result = check_connection("imap.gmail.com", DEFAULT_IMAP_PORT, "a@gmail.com", "wrong")
    assert result.success is False
    assert result.kind == "auth_error"


def test_dns_failure(monkeypatch):
    def _raise_gaierror(*args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(imaplib, "IMAP4_SSL", _raise_gaierror)
    result = check_connection("no-such-host.invalid", DEFAULT_IMAP_PORT, "a@gmail.com", "pw")
    assert result.success is False
    assert result.kind == "network_error"


def test_connection_refused(monkeypatch):
    def _raise_refused(*args, **kwargs):
        raise ConnectionRefusedError("Connection refused")

    monkeypatch.setattr(imaplib, "IMAP4_SSL", _raise_refused)
    result = check_connection("localhost", 1, "a@gmail.com", "pw")
    assert result.success is False
    assert result.kind == "network_error"


def test_timeout(monkeypatch):
    def _raise_timeout(*args, **kwargs):
        raise socket.timeout("timed out")

    monkeypatch.setattr(imaplib, "IMAP4_SSL", _raise_timeout)
    result = check_connection("imap.example.com", DEFAULT_IMAP_PORT, "a@example.com", "pw")
    assert result.success is False
    assert result.kind == "network_error"


@pytest.mark.parametrize(
    "server,username,password",
    [
        ("", "a@gmail.com", "pw"),
        ("imap.gmail.com", "", "pw"),
        ("imap.gmail.com", "a@gmail.com", ""),
    ],
)
def test_missing_fields(server, username, password):
    result = check_connection(server, DEFAULT_IMAP_PORT, username, password)
    assert result.success is False
    assert result.kind == "unknown_error"


def test_logout_failure_does_not_mask_success(monkeypatch):
    """If LOGOUT itself errors after a successful login, the test should
    still report success — the credentials were proven valid."""

    class _FakeImapOkButBadLogout(_FakeImapOk):
        def logout(self):
            raise OSError("connection already closed")

    monkeypatch.setattr(imaplib, "IMAP4_SSL", _FakeImapOkButBadLogout)
    result = check_connection("imap.gmail.com", DEFAULT_IMAP_PORT, "a@gmail.com", "app-pw")
    assert result.success is True
