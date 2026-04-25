"""
Tests for RunShape route generation backend.
Run with: pytest tests/test_route_generator.py -v
"""

import math
import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from route_generator import (
    PatternGenerator, DistanceGenerator, Pattern, ElevationProfile,
    haversine_km, total_distance_km, estimate_elevation_gain,
    estimate_time_min, coords_to_gpx, RouteRequest, generate_route,
)

LAT, LON = -27.4698, 153.0251  # Brisbane CBD


# ─── PATTERN GENERATORS ───────────────────────────────────────────────────────

class TestPatternGenerators:

    def test_loop_returns_closed_path(self):
        pts = PatternGenerator.loop(LAT, LON)
        assert pts[0] == pytest.approx(pts[-1], abs=1e-6)

    def test_loop_has_expected_points(self):
        pts = PatternGenerator.loop(LAT, LON)
        assert len(pts) == 25

    def test_figure8_crosses_center(self):
        pts = PatternGenerator.figure_8(LAT, LON)
        lats = [p[0] for p in pts]
        assert min(lats) < LAT < max(lats), "Figure-8 should cross the centre lat"

    def test_star_has_5_outer_points(self):
        pts = PatternGenerator.star(LAT, LON, scale=1.0)
        # Every other point is an outer spike (exclude closing point)
        outer = [pts[i] for i in range(0, len(pts)-1, 2)]
        assert len(outer) >= 5

    def test_lollipop_starts_and_ends_at_origin(self):
        pts = PatternGenerator.lollipop(LAT, LON)
        assert pts[0][0] == pytest.approx(LAT, abs=1e-6)
        assert pts[-1][0] == pytest.approx(LAT, abs=1e-4)

    def test_scale_affects_size(self):
        pts1 = PatternGenerator.loop(LAT, LON, scale=1.0)
        pts2 = PatternGenerator.loop(LAT, LON, scale=2.0)
        d1 = total_distance_km(pts1)
        d2 = total_distance_km(pts2)
        assert d2 > d1 * 1.5, "Larger scale should produce a longer route"

    def test_all_patterns_generate_coords(self):
        for pattern in Pattern:
            pts = PatternGenerator.generate(pattern, LAT, LON, scale=1.0)
            assert len(pts) >= 5, f"{pattern} should produce at least 5 points"
            for lat, lon in pts:
                assert -90 <= lat <= 90
                assert -180 <= lon <= 180

    def test_unknown_pattern_raises(self):
        with pytest.raises((ValueError, KeyError)):
            PatternGenerator.generate("triangle", LAT, LON)


# ─── DISTANCE GENERATOR ───────────────────────────────────────────────────────

class TestDistanceGenerator:

    def test_circular_target_distance(self):
        target = 10.0
        pts = DistanceGenerator.circular(LAT, LON, target, scale=1.0)
        dist = total_distance_km(pts)
        # Allow 30% tolerance (raw waypoints, no road snap)
        assert abs(dist - target) / target < 0.30

    def test_circular_scale_increases_distance(self):
        pts1 = DistanceGenerator.circular(LAT, LON, 5.0, scale=1.0)
        pts2 = DistanceGenerator.circular(LAT, LON, 5.0, scale=1.5)
        assert total_distance_km(pts2) > total_distance_km(pts1)

    def test_circular_returns_closed_loop(self):
        pts = DistanceGenerator.circular(LAT, LON, 5.0)
        assert pts[0][0] == pytest.approx(pts[-1][0], abs=1e-6)


# ─── METRICS ──────────────────────────────────────────────────────────────────

class TestMetrics:

    def test_haversine_known_distance(self):
        # Brisbane CBD to Gold Coast ~75 km
        brisbane = (-27.47, 153.02)
        gold_coast = (-28.00, 153.43)
        d = haversine_km(brisbane, gold_coast)
        assert 70 < d < 85

    def test_haversine_same_point(self):
        assert haversine_km((LAT, LON), (LAT, LON)) == pytest.approx(0, abs=1e-9)

    def test_total_distance_single_segment(self):
        a, b = (0.0, 0.0), (0.0, 1.0)
        d = total_distance_km([a, b])
        assert d == pytest.approx(haversine_km(a, b))

    def test_elevation_gain_increases_with_profile(self):
        dist = 10.0
        gains = [estimate_elevation_gain(dist, p) for p in ElevationProfile]
        assert gains == sorted(gains), "Elevation gain should increase with difficulty"

    def test_elevation_gain_scales_with_distance(self):
        g1 = estimate_elevation_gain(5.0, ElevationProfile.MODERATE)
        g2 = estimate_elevation_gain(10.0, ElevationProfile.MODERATE)
        assert g2 == pytest.approx(g1 * 2, rel=0.05)

    def test_time_increases_with_elevation(self):
        t1 = estimate_time_min(10.0, 100)
        t2 = estimate_time_min(10.0, 500)
        assert t2 > t1

    def test_time_min_reasonable(self):
        # 10 km with flat profile should be ~65-80 min
        t = estimate_time_min(10.0, estimate_elevation_gain(10.0, ElevationProfile.FLAT))
        assert 55 < t < 90


# ─── GPX EXPORT ───────────────────────────────────────────────────────────────

class TestGPXExport:

    def test_gpx_contains_trackpoints(self):
        coords = [(LAT, LON), (LAT + 0.001, LON + 0.001)]
        gpx = coords_to_gpx(coords)
        assert "<trkpt" in gpx
        assert f'lat="{LAT:.6f}"' in gpx

    def test_gpx_valid_xml_structure(self):
        coords = [(LAT, LON)]
        gpx = coords_to_gpx(coords, name="Test Route")
        assert gpx.startswith("<?xml")
        assert "<gpx" in gpx
        assert "</gpx>" in gpx
        assert "Test Route" in gpx

    def test_gpx_point_count_matches(self):
        coords = [(LAT + i * 0.001, LON + i * 0.001) for i in range(10)]
        gpx = coords_to_gpx(coords)
        assert gpx.count("<trkpt") == 10


# ─── INTEGRATION ──────────────────────────────────────────────────────────────

class TestIntegration:

    def test_pattern_route_no_snap(self):
        req = RouteRequest(
            lat=LAT, lon=LON,
            mode="pattern",
            pattern=Pattern.LOOP,
            scale=1.0,
            elevation=ElevationProfile.FLAT,
        )
        result = generate_route(req, snap_to_roads=False)
        assert result.distance_km > 0
        assert result.elevation_gain_m >= 0
        assert result.estimated_time_min > 0
        assert len(result.coordinates) >= 5
        assert result.gpx is not None

    def test_distance_route_no_snap(self):
        req = RouteRequest(
            lat=LAT, lon=LON,
            mode="distance",
            distance_km=5.0,
            scale=1.0,
            elevation=ElevationProfile.MODERATE,
        )
        result = generate_route(req, snap_to_roads=False)
        assert 3 < result.distance_km < 8  # ~30% tolerance

    def test_missing_pattern_raises(self):
        req = RouteRequest(lat=LAT, lon=LON, mode="pattern")
        with pytest.raises(ValueError, match="pattern"):
            generate_route(req, snap_to_roads=False)

    def test_missing_distance_raises(self):
        req = RouteRequest(lat=LAT, lon=LON, mode="distance")
        with pytest.raises(ValueError, match="distance"):
            generate_route(req, snap_to_roads=False)
