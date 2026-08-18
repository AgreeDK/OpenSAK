"""tests/unit-tests/test_get_nearby_caches_748_743.py — issues #748, #743.

Own module/DB (separate from test_get_nearby_caches_718.py's shared,
precisely-counted dataset) so seeding extra caches with corrected
coordinates and an active filter here can't shift that file's existing
exact-count assertions.

#748: map_widget.py plots a cache at its corrected coordinates when set
(`c.corrected ? c.clat : c.lat` in loadCaches() JS), so get_nearby_caches()
must compute radius membership/sort order from the same effective
(corrected-aware) coordinates — not raw latitude/longitude — or a cache can
pass the raw-coordinate radius check yet render outside the drawn circle
(or a genuinely nearby corrected cache gets missed).

#743: get_nearby_caches() previously only ever filtered by distance,
ignoring whatever filter was currently active on the main list — selecting
a cache while filtered made the split-screen map silently revert to
showing every nearby cache.
"""

import pytest

from opensak.db.database import get_session
from opensak.db.models import Cache, UserNote
from opensak.filters.engine import FilterSet, GcCodeFilter, get_nearby_caches

LONDON_LAT, LONDON_LON = 51.5074, -0.1278


@pytest.fixture(scope="module", autouse=True)
def seed_data(tmp_db):
    with get_session() as s:
        selected = Cache(
            gc_code="GCSEL000", name="Selected", cache_type="Traditional Cache",
            latitude=LONDON_LAT, longitude=LONDON_LON,
        )
        s.add(selected)

        plain_nearby = Cache(
            gc_code="GCPLAIN1", name="Plain nearby, no correction",
            cache_type="Traditional Cache",
            latitude=LONDON_LAT + 0.005, longitude=LONDON_LON,  # ~0.56 km
        )
        s.add(plain_nearby)

        # Raw coords ~33 km out (well outside a 2 km radius, but inside the
        # widened SQL pre-filter net) — corrected coords ~0.56 km out.
        # Must be INCLUDED once corrected coordinates are honoured.
        corrected_in = Cache(
            gc_code="GCCORRIN", name="Corrected into radius",
            cache_type="Traditional Cache",
            latitude=LONDON_LAT + 0.3, longitude=LONDON_LON,  # ~33 km raw
        )
        s.add(corrected_in)
        s.flush()
        s.add(UserNote(
            cache_id=corrected_in.id, is_corrected=True,
            corrected_lat=LONDON_LAT + 0.005, corrected_lon=LONDON_LON,
        ))

        # Raw coords ~0.56 km out (well within a 2 km radius) — corrected
        # coords ~33 km out. Must be EXCLUDED once corrected coordinates
        # are honoured, even though its raw position would pass.
        corrected_out = Cache(
            gc_code="GCCOROUT", name="Corrected out of radius",
            cache_type="Traditional Cache",
            latitude=LONDON_LAT + 0.006, longitude=LONDON_LON,  # ~0.67 km raw
        )
        s.add(corrected_out)
        s.flush()
        s.add(UserNote(
            cache_id=corrected_out.id, is_corrected=True,
            corrected_lat=LONDON_LAT + 0.3, corrected_lon=LONDON_LON,
        ))

        # A UserNote row that exists but isn't actually a correction
        # (is_corrected=False) must be treated exactly like having none —
        # raw coordinates still apply.
        uncorrected_note = Cache(
            gc_code="GCUNCORR", name="Has a note, but not corrected",
            cache_type="Traditional Cache",
            latitude=LONDON_LAT + 0.007, longitude=LONDON_LON,  # ~0.78 km raw
        )
        s.add(uncorrected_note)
        s.flush()
        s.add(UserNote(
            cache_id=uncorrected_note.id, is_corrected=False,
            corrected_lat=LONDON_LAT + 5.0, corrected_lon=LONDON_LON,
        ))


class TestCorrectedCoordinates:
    def test_corrected_coords_include_cache_despite_far_raw_coords(self):
        with get_session() as s:
            nearby, _ = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
            )
        assert "GCCORRIN" in {c.gc_code for c in nearby}

    def test_corrected_coords_exclude_cache_despite_near_raw_coords(self):
        with get_session() as s:
            nearby, _ = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
            )
        assert "GCCOROUT" not in {c.gc_code for c in nearby}

    def test_non_corrected_note_does_not_affect_position(self):
        with get_session() as s:
            nearby, _ = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
            )
        # Raw coords (~0.78 km) are within radius; the note's stray
        # corrected_lat/lon (is_corrected=False) must be ignored, not
        # accidentally pull it ~555 km away and out of the result.
        assert "GCUNCORR" in {c.gc_code for c in nearby}

    def test_total_and_membership_consistent(self):
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
            )
        codes = {c.gc_code for c in nearby}
        assert codes == {"GCSEL000", "GCPLAIN1", "GCCORRIN", "GCUNCORR"}
        assert total == len(codes) == 4


class TestActiveFilterScoping:
    def test_no_filterset_returns_full_nearby_set(self):
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
                filterset=None,
            )
        assert total == 4

    def test_filterset_narrows_nearby_results(self):
        # Matches only GCSEL000 and GCPLAIN1 — GCCORRIN/GCUNCORR excluded
        # by the filter despite being geographically within radius.
        fs = FilterSet(mode="OR")
        fs.add(GcCodeFilter("GCSEL000"))
        fs.add(GcCodeFilter("GCPLAIN1"))
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
                filterset=fs,
            )
        codes = {c.gc_code for c in nearby}
        assert codes == {"GCSEL000", "GCPLAIN1"}
        assert total == 2

    def test_empty_filterset_behaves_same_as_none(self):
        with get_session() as s:
            nearby_none, total_none = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
                filterset=None,
            )
            nearby_empty, total_empty = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
                filterset=FilterSet(),
            )
        assert {c.gc_code for c in nearby_none} == {c.gc_code for c in nearby_empty}
        assert total_none == total_empty

    def test_filterset_matching_nothing_returns_empty(self):
        fs = FilterSet().add(GcCodeFilter("GCNOMATCH"))
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
                filterset=fs,
            )
        assert nearby == []
        assert total == 0
