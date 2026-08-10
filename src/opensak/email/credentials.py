"""
src/opensak/email/credentials.py — secure storage for e-mail account
passwords (issue #443).

Uses the `keyring` package, which stores secrets in the platform's native
credential store:
  Windows: Credential Locker
  macOS:   Keychain
  Linux:   Secret Service (e.g. GNOME Keyring, KWallet)

Passwords are NEVER written to opensak.json or any other plain-text file.
Non-secret connection settings (server, port, username) are stored
separately via settings_store / AppSettings — see
opensak.gui.settings.AppSettings.email_pq_*.

Keyring lookups can raise on some minimal Linux setups with no backend
configured (e.g. a headless CI runner). Callers should treat a raised
exception the same as "no password saved" rather than letting it crash
the UI — see the try/except wrapping below.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Single logical "application" in the OS credential store. Entries within
# it are keyed by the e-mail account's username (see save/load/delete
# below), so this stays a single constant even if OpenSAK later supports
# more than one saved e-mail account.
_SERVICE_NAME = "OpenSAK-EmailPQ"


def save_password(username: str, password: str) -> None:
    """Gem (eller overskriv) adgangskoden for `username` i OS' keyring.

    Rejser videre hvis keyring-backend fejler — kaldere i UI-laget bør
    fange og vise en fejlbesked, da en stille fejl her ville efterlade
    brugeren i den tro at adgangskoden er gemt, når den ikke er.
    """
    import keyring
    keyring.set_password(_SERVICE_NAME, username, password)


def load_password(username: str) -> str | None:
    """Hent den gemte adgangskode for `username`, eller None hvis ingen
    findes (eller keyring-backend ikke er tilgængelig)."""
    if not username:
        return None
    import keyring
    try:
        return keyring.get_password(_SERVICE_NAME, username)
    except Exception:
        logger.warning(
            "Could not read from OS keyring for %r — treating as no saved password",
            username,
            exc_info=True,
        )
        return None


def delete_password(username: str) -> None:
    """Slet den gemte adgangskode for `username`, hvis den findes.

    Fejler stille hvis der ikke er nogen gemt adgangskode eller hvis
    keyring-backend ikke er tilgængelig — sletning af noget der ikke
    findes skal ikke være en fejl for kalderen.
    """
    if not username:
        return
    import keyring
    from keyring.errors import PasswordDeleteError
    try:
        keyring.delete_password(_SERVICE_NAME, username)
    except PasswordDeleteError:
        pass
    except Exception:
        logger.warning(
            "Could not delete from OS keyring for %r", username, exc_info=True
        )


def has_password(username: str) -> bool:
    """Bekvem helper: findes der en gemt adgangskode for `username`?"""
    return load_password(username) is not None
