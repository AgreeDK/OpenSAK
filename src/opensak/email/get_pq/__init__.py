"""
src/opensak/email/get_pq/ — Pocket Query retrieval from e-mail (issue #443).

Session 1 scope (this delivery): `connection.py` — generic IMAP + app-
password connection testing, used by the Settings dialog's PQ Email tab.

Planned for later sessions, not yet implemented:
  - parser.py   — recognise Geocaching.com's "PQ ready" notification
                  e-mail and extract the attached zip
  - service.py  — orchestrate fetch → import → DB match → mark-as-read,
                  reusing the existing GPX/PQ zip import pipeline

Kept as a separate subpackage (rather than folding into `opensak.email`
directly) so a future e-mail-based feature can live alongside this one
without the two becoming entangled.
"""
