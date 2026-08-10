"""
src/opensak/email/get_pq/connection.py — generic IMAP connection testing
(issue #443, session 1).

Covers Gmail, iCloud, one.com and most other providers that still accept
a plain username/password (typically an app-specific password) over
IMAP. Does NOT cover Outlook.com/Live.com — Microsoft has fully
deprecated password-based IMAP for consumer accounts, OAuth2 is
mandatory there (tracked separately in #698).

This module is intentionally translation-free (no `tr()` calls) and has
no Qt dependency, so it can be unit-tested in isolation and reused by a
future background-check worker without pulling in the GUI layer. Callers
in the GUI layer map `ConnectionTestResult.kind` to a translated message.
"""

from __future__ import annotations

import imaplib
import socket
import ssl
from dataclasses import dataclass
from typing import Literal

ConnectionTestKind = Literal["success", "auth_error", "network_error", "unknown_error"]

# Most providers that support plain IMAP+password default to implicit
# SSL/TLS on this port (Gmail, iCloud, one.com, Outlook/Live's *old*
# now-defunct basic-auth endpoint, etc.) — used to prefill the Settings
# dialog's Port field, not enforced as the only allowed value.
DEFAULT_IMAP_PORT = 993

# Keep the test snappy: a wrong hostname/unreachable server should fail
# within a few seconds, not hang the "Test" button indefinitely.
_CONNECT_TIMEOUT_SECONDS = 10


@dataclass
class ConnectionTestResult:
    success: bool
    kind: ConnectionTestKind
    detail: str  # raw technical detail (English), for logs — not for direct display


def check_connection(
    server: str,
    port: int,
    username: str,
    password: str,
) -> ConnectionTestResult:
    """Forsøg at logge ind på en IMAP-server med brugernavn/adgangskode.

    Lukker forbindelsen igen med det samme uanset udfald — dette er kun
    en verifikation af at credentials virker, ikke starten på en
    session der bruges videre.
    """
    server = server.strip()
    username = username.strip()

    if not server or not username or not password:
        return ConnectionTestResult(
            success=False,
            kind="unknown_error",
            detail="Missing server, username or password.",
        )

    try:
        conn = imaplib.IMAP4_SSL(server, port, timeout=_CONNECT_TIMEOUT_SECONDS)
    except (socket.gaierror, socket.timeout, ConnectionRefusedError, OSError) as exc:
        return ConnectionTestResult(
            success=False, kind="network_error", detail=f"{type(exc).__name__}: {exc}"
        )
    except ssl.SSLError as exc:
        return ConnectionTestResult(
            success=False, kind="network_error", detail=f"SSLError: {exc}"
        )

    try:
        try:
            conn.login(username, password)
        except imaplib.IMAP4.error as exc:
            return ConnectionTestResult(
                success=False, kind="auth_error", detail=str(exc)
            )
        return ConnectionTestResult(success=True, kind="success", detail="OK")
    except (socket.timeout, OSError) as exc:
        return ConnectionTestResult(
            success=False, kind="network_error", detail=f"{type(exc).__name__}: {exc}"
        )
    except Exception as exc:  # pragma: no cover - defensive catch-all
        return ConnectionTestResult(
            success=False, kind="unknown_error", detail=f"{type(exc).__name__}: {exc}"
        )
    finally:
        try:
            conn.logout()
        except Exception:
            pass  # already broken, or IMAP4.error on a server that dislikes LOGOUT pre-select — ignore
