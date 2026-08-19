# tests/unit-tests/test_gsak_found_status_import.py — issue #766 (Allyn56
# round-trip testing): found status not carrying over from a genuine GSAK
# GPX/GGZ export.
#
# GSAK's own GPX/GGZ export does NOT set sym="Geocache Found" the way the
# GC.com Pocket Query convention does -- <sym> from a real GSAK export just
# reflects the cache type icon regardless of found state. The importer's
# #766 log-based found fallback originally only ran when <sym> was entirely
# ABSENT, which protected OpenSAK's own re-export (sym is always present and
# authoritative there) but also meant found status from a genuine GSAK
# export -- where sym IS present but doesn't mean anything -- was silently
# dropped.
#
# The fix: detect genuine GSAK origin via the presence of any GSAK-only
# wptExtension field that OpenSAK's own export never writes (UserFlag,
# FirstToFind, UserSort, IsPremium, UserData/User2-4, FavPoints, County,
# LatN/LongE, LatBeforeCorrect/LonBeforeCorrect) -- OpenSAK only ever writes
# gsak:UserNote. When one of those is present, the log-based fallback runs
# even though <sym> is present.

import textwrap
from pathlib import Path

import pytest

from opensak.db.database import get_session, init_db
from opensak.db.models import Cache
from opensak.importer import import_gpx


@pytest.fixture()
def fresh_db(tmp_path):
    db_path = tmp_path / "gsak_found.db"
    init_db(db_path=db_path)
    return db_path


@pytest.fixture()
def found_username():
    from opensak.gui.settings import get_settings
    get_settings().gc_username = "AB Green"
    get_settings().gc_finder_id = ""


def _write_gpx(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "test.gpx"
    p.write_text(content, encoding="utf-8")
    return p


def _gsak_gpx(*, sym: str = "Geocache", gsak_extension: str, log_date: str = "2024-03-01T00:00:00Z") -> str:
    # Mirrors a real GSAK GPX export: <sym> reflects the cache TYPE icon
    # (never "Geocache Found"), the found-type log is present in the
    # groundspeak:logs block, and the wptExtension carries GSAK-only
    # fields (here: UserFlag) that OpenSAK's own export never writes.
    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="utf-8"?>
        <gpx xmlns="http://www.topografix.com/GPX/1/0"
             xmlns:groundspeak="http://www.groundspeak.com/cache/1/0/1"
             xmlns:gsak="http://www.gsak.net/xmlv1/6"
             version="1.0" creator="GSAK">
          <wpt lat="55.0000" lon="10.0000">
            <time>2024-01-01T00:00:00</time>
            <n>GCFOUNDG1</n>
            <urlname>Test Cache</urlname>
            <sym>{sym}</sym>
            <type>Geocache|Traditional Cache</type>
            <groundspeak:cache id="1" archived="False" available="True">
              <groundspeak:name>Test Cache</groundspeak:name>
              <groundspeak:placed_by>Owner</groundspeak:placed_by>
              <groundspeak:type>Traditional Cache</groundspeak:type>
              <groundspeak:container>Small</groundspeak:container>
              <groundspeak:difficulty>2.0</groundspeak:difficulty>
              <groundspeak:terrain>2.0</groundspeak:terrain>
              <groundspeak:logs>
                <groundspeak:log id="9001">
                  <groundspeak:date>{log_date}</groundspeak:date>
                  <groundspeak:type>Found it</groundspeak:type>
                  <groundspeak:finder id="999">AB Green</groundspeak:finder>
                  <groundspeak:text encoded="False">TFTC</groundspeak:text>
                </groundspeak:log>
              </groundspeak:logs>
            </groundspeak:cache>
            {gsak_extension}
          </wpt>
        </gpx>
    """)


def test_gsak_export_found_status_detected_via_userflag(tmp_path, fresh_db, found_username):
    # Genuine GSAK export: sym is present but plain ("Geocache"), never
    # "Geocache Found" -- only the GSAK-only UserFlag field marks this as a
    # real GSAK file, and only the log list identifies the find.
    gpx = _gsak_gpx(gsak_extension="""
            <gsak:wptExtension>
              <gsak:UserFlag>True</gsak:UserFlag>
            </gsak:wptExtension>""")
    f = _write_gpx(tmp_path, gpx)
    with get_session() as s:
        import_gpx(f, s)
        cache = s.query(Cache).filter_by(gc_code="GCFOUNDG1").one()
        assert cache.found is True
        assert cache.found_date is not None
        assert cache.found_date.year == 2024


def test_gsak_export_found_status_detected_via_lat_before_correct(tmp_path, fresh_db, found_username):
    # Same scenario, but the GSAK fingerprint comes from corrected-coords
    # fields (LatBeforeCorrect/LonBeforeCorrect) instead of UserFlag.
    gpx = _gsak_gpx(gsak_extension="""
            <gsak:wptExtension>
              <gsak:LatBeforeCorrect>55.1000</gsak:LatBeforeCorrect>
              <gsak:LonBeforeCorrect>10.1000</gsak:LonBeforeCorrect>
            </gsak:wptExtension>""")
    f = _write_gpx(tmp_path, gpx)
    with get_session() as s:
        import_gpx(f, s)
        cache = s.query(Cache).filter_by(gc_code="GCFOUNDG1").one()
        assert cache.found is True


def test_gsak_export_without_fingerprint_still_uses_old_guard(tmp_path, fresh_db, found_username):
    # Regression guard: a plain <sym>Geocache</sym> with NO GSAK-only
    # wptExtension fields at all (e.g. only gsak:UserNote, matching
    # OpenSAK's own re-export) must still be treated as authoritative
    # "not found" -- the fallback must not fire just because a
    # gsak:wptExtension element exists.
    gpx = _gsak_gpx(gsak_extension="""
            <gsak:wptExtension>
              <gsak:UserNote>Nice spot.</gsak:UserNote>
            </gsak:wptExtension>""")
    f = _write_gpx(tmp_path, gpx)
    with get_session() as s:
        import_gpx(f, s)
        cache = s.query(Cache).filter_by(gc_code="GCFOUNDG1").one()
        assert cache.found is False


def test_gsak_export_sym_geocache_found_still_honoured_directly(tmp_path, fresh_db, found_username):
    # If a GSAK export ever DOES say sym="Geocache Found" outright, it's
    # still honoured directly regardless of the GSAK fingerprint.
    gpx = _gsak_gpx(
        sym="Geocache Found",
        gsak_extension="""
            <gsak:wptExtension>
              <gsak:UserFlag>True</gsak:UserFlag>
            </gsak:wptExtension>""",
    )
    f = _write_gpx(tmp_path, gpx)
    with get_session() as s:
        import_gpx(f, s)
        cache = s.query(Cache).filter_by(gc_code="GCFOUNDG1").one()
        assert cache.found is True
