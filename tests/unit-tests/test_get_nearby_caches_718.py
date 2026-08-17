"""tests/unit-tests/test_get_nearby_caches_718.py — issue #718.

get_nearby_caches() feeds the split-screen map: given a selected cache's
coordinates, it returns that cache's neighbours within radius_km,
nearest-first, capped to max_caches — independent of the overview map's
own map_max_caches cap and current sort order (the root cause of #718:
a cache outside that dataset had no map at all, or the wrong one).

Deliberately seeds caches with a *stale* Cache.distance column (relative
to the app's home point) that would give the WRONG order if the function
mistakenly sorted via SortSpec("distance", ...) instead of computing
distance from the (lat, lon) actually passed in — see the "wrong sort
field" bug caught during implementation (SortSpec("distance") always
sorts by distance-from-home, not distance-from-selected-cache).
"""

import pytest

from opensak.db.database import get_session
from opensak.db.models import Cache
from opensak.filters.engine import get_nearby_caches


# Selected cache: sits in "London" for the test, far from the app's
# nominal home point. Neighbours are placed at known, increasing
# straight-line distances from London so ordering is unambiguous.
LONDON_LAT, LONDON_LON = 51.5074, -0.1278


@pytest.fixture(scope="module", autouse=True)
def seed_nearby_data(tmp_db):
    caches = [
        # The selected cache itself — distance 0 from itself.
        Cache(
            gc_code="GCLDN000", name="Selected London Cache",
            cache_type="Traditional Cache",
            latitude=LONDON_LAT, longitude=LONDON_LON,
            distance=9999.0,  # stale home-point distance — must NOT drive ordering
        ),
        # Neighbours within ~2km, at increasing distance, but seeded with
        # Cache.distance values in a DIFFERENT (in fact reversed) order —
        # so a test that accidentally sorts by the stored column instead
        # of true distance from (LONDON_LAT, LONDON_LON) will fail loudly.
        Cache(
            gc_code="GCLDN001", name="Nearest neighbour", cache_type="Traditional Cache",
            latitude=LONDON_LAT + 0.005, longitude=LONDON_LON,  # ~0.56 km
            distance=50.0,
        ),
        Cache(
            gc_code="GCLDN002", name="Second neighbour", cache_type="Traditional Cache",
            latitude=LONDON_LAT + 0.01, longitude=LONDON_LON,  # ~1.11 km
            distance=30.0,
        ),
        Cache(
            gc_code="GCLDN003", name="Third neighbour", cache_type="Traditional Cache",
            latitude=LONDON_LAT + 0.015, longitude=LONDON_LON,  # ~1.67 km
            distance=10.0,
        ),
        # Just outside a 2km radius.
        Cache(
            gc_code="GCLDN004", name="Just outside radius", cache_type="Traditional Cache",
            latitude=LONDON_LAT + 0.03, longitude=LONDON_LON,  # ~3.34 km
            distance=1.0,
        ),
        # Far away entirely (e.g. "Copenhagen") — near the app's home
        # point, so it WOULD sort first if the bug reappeared.
        Cache(
            gc_code="GCCPH001", name="Copenhagen cache", cache_type="Traditional Cache",
            latitude=55.6761, longitude=12.5683,
            distance=0.1,
        ),
    ]
    with get_session() as s:
        for c in caches:
            s.add(c)


class TestRadiusBoundary:
    def test_only_caches_within_radius_returned(self):
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
            )
        codes = {c.gc_code for c in nearby}
        assert codes == {"GCLDN000", "GCLDN001", "GCLDN002", "GCLDN003"}
        assert total == 4

    def test_far_away_cache_excluded_even_with_smallest_stored_distance(self):
        # GCCPH001 has the smallest *stored* Cache.distance (0.1) of all
        # seeded rows, but is geographically nowhere near London — must
        # never appear in a London-centered query.
        with get_session() as s:
            nearby, _ = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
            )
        assert "GCCPH001" not in {c.gc_code for c in nearby}

    def test_wider_radius_includes_more_neighbours(self):
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=5.0, max_caches=500,
            )
        codes = {c.gc_code for c in nearby}
        assert "GCLDN004" in codes
        assert total == 5


class TestOrdering:
    def test_results_sorted_nearest_first_by_true_distance(self):
        # Seeded Cache.distance column is reverse order on purpose (see
        # fixture docstring) — this must sort by real distance from
        # (LONDON_LAT, LONDON_LON), not by the stored column.
        with get_session() as s:
            nearby, _ = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
            )
        assert [c.gc_code for c in nearby] == [
            "GCLDN000", "GCLDN001", "GCLDN002", "GCLDN003",
        ]


class TestMaxCachesCap:
    def test_cap_limits_returned_list_but_not_total(self):
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=2,
            )
        assert [c.gc_code for c in nearby] == ["GCLDN000", "GCLDN001"]
        assert total == 4  # full count within radius, unaffected by cap

    def test_cap_larger_than_result_set_returns_all(self):
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=2.0, max_caches=500,
            )
        assert len(nearby) == total == 4


class TestEdgeCases:
    def test_none_coordinates_return_empty(self):
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, None, None, radius_km=2.0, max_caches=500,
            )
        assert nearby == []
        assert total == 0

    def test_zero_radius_returns_only_coincident_cache(self):
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, LONDON_LAT, LONDON_LON, radius_km=0.0, max_caches=500,
            )
        assert [c.gc_code for c in nearby] == ["GCLDN000"]
        assert total == 1

    def test_no_matches_in_empty_area_returns_empty(self):
        with get_session() as s:
            nearby, total = get_nearby_caches(
                s, 0.0, 0.0, radius_km=1.0, max_caches=500,
            )
        assert nearby == []
        assert total == 0
