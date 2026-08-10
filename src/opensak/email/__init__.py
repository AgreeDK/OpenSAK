"""
src/opensak/email/ — e-mail account integration.

Root package for anything OpenSAK does with the user's own e-mail account.
Currently contains `get_pq/` (issue #443 — fetching Pocket Query zips
mailed by Geocaching.com). Future e-mail-related features should live in
their own subpackage here rather than growing this feature's code.

`credentials.py` (this package) is shared infrastructure: secure storage
of e-mail account passwords via the OS credential store, independent of
what the credentials are used for.
"""
