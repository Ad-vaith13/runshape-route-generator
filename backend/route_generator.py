"""
RunShape - Route Generation Backend
====================================
Core algorithms for generating shaped running routes.
Supports both pattern-based and distance-based route planning.
"""

import math
import json
import requests
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


# ─── TYPES ────────────────────────────────────────────────────────────────────

Coord = Tuple[float, float]  # (lat, lon)


class Pattern(str, Enum):
    LOOP = "loop"
    FIGURE_8 = "figure8"
    STAR = "star"
    SPIRAL = "spiral"
    LOLLIPOP = "lollipop"
    ZIGZAG = "zigzag"


class ElevationProfile(str, Enum):
    FLAT = "flat"
    MODERATE = "moderate"
    HILLY = "hilly"
    CHALLENGING = "challenging"


@dataclass
class RouteRequest:
    lat: float
    lon: float
    mode: str                           # "pattern" | "distance"
    pattern: Optional[Pattern] = None
    distance_km: Optional[float] = None
    scale: float = 1.0
    elevation: ElevationProfile = ElevationProfile.FLAT


@dataclass
class RouteResult:
    coordinates: List[Coord]
    distance_km: float
    elevation_gain_m: int
    estimated_time_min: int
    pattern_used: str
    gpx: Optional[str] = None


# ─── WAYPOINT GENERATORS ──────────────────────────────────────────────────────

class PatternGenerator:
    """Generates geometric waypoints that approximate running patterns."""

    @staticmethod
    def loop(lat: float, lon: float, scale: float = 1.0) -> List[Coord]:
        """Simple circular loop."""
        r_lat = 0.008 * scale
        r_lon = r_lat / math.cos(math.radians(lat))
        n = 24
        pts = []
        for i in range(n + 1):
            angle = (i / n) * 2 * math.pi - math.pi / 2
            pts.append((
                lat + r_lat * math.cos(angle),
                lon + r_lon * math.sin(angle)
            ))
        return pts

    @staticmethod
    def figure_8(lat: float, lon: float, scale: float = 1.0) -> List[Coord]:
        """Figure-of-eight (lemniscate of Bernoulli)."""
        r = 0.006 * scale
        r_lon = r / math.cos(math.radians(lat))
        n = 72
        pts = []
        for i in range(n + 1):
            t = (i / n) * 4 * math.pi
            pts.append((
                lat + r * math.sin(t),
                lon + r_lon * math.sin(t) * math.cos(t)
            ))
        return pts

    @staticmethod
    def star(lat: float, lon: float, scale: float = 1.0) -> List[Coord]:
        """5-pointed star route."""
        outer_r = 0.009 * scale
        inner_r = 0.004 * scale
        pts = []
        for i in range(11):
            r = outer_r if i % 2 == 0 else inner_r
            angle = (i / 10) * 2 * math.pi - math.pi / 2
            r_lon = r / math.cos(math.radians(lat))
            pts.append((
                lat + r * math.cos(angle),
                lon + r_lon * math.sin(angle)
            ))
        pts.append(pts[0])  # close
        return pts

    @staticmethod
    def spiral(lat: float, lon: float, scale: float = 1.0) -> List[Coord]:
        """Outward spiral then back."""
        pts = []
        n = 60
        turns = 2.5
        for i in range(n + 1):
            t = (i / n) * turns * 2 * math.pi
            r = (0.001 + 0.003 * (i / n)) * scale
            r_lon = r / math.cos(math.radians(lat))
            pts.append((lat + r * math.cos(t), lon + r_lon * math.sin(t)))
        # Return spiral
        for i in range(n, -1, -1):
            t = (i / n) * turns * 2 * math.pi + math.pi
            r = (0.001 + 0.003 * (i / n)) * scale * 0.7
            r_lon = r / math.cos(math.radians(lat))
            pts.append((lat + r * math.cos(t), lon + r_lon * math.sin(t)))
        return pts

    @staticmethod
    def lollipop(lat: float, lon: float, scale: float = 1.0) -> List[Coord]:
        """Straight out, loop, straight back."""
        stem = 0.012 * scale
        r = 0.006 * scale
        r_lon = r / math.cos(math.radians(lat))
        stem_lon = stem / math.cos(math.radians(lat))

        pts = [(lat, lon)]
        # Run out along stem
        for i in range(1, 8):
            pts.append((lat + stem * (i / 7), lon))
        # Circle at the top
        top_lat = lat + stem
        n = 36
        for i in range(n + 1):
            angle = (i / n) * 2 * math.pi - math.pi / 2
            pts.append((
                top_lat + r * math.cos(angle),
                lon + r_lon * math.sin(angle)
            ))
        # Return down stem
        for i in range(7, -1, -1):
            pts.append((lat + stem * (i / 7), lon))
        return pts

    @staticmethod
    def zigzag(lat: float, lon: float, scale: float = 1.0) -> List[Coord]:
        """Zigzag out and back."""
        w = 0.006 * scale
        h = 0.005 * scale
        w_lon = w / math.cos(math.radians(lat))
        pts = []
        n_zigs = 5
        for i in range(n_zigs):
            x = -2 * w + i * w
            y = h if i % 2 == 0 else -h
            pts.append((lat + y, lon + x / math.cos(math.radians(lat))))
        for i in range(n_zigs - 1, -1, -1):
            x = -2 * w + i * w
            y = -h if i % 2 == 0 else h
            pts.append((lat + y, lon + x / math.cos(math.radians(lat))))
        pts.append(pts[0])
        return pts

    @classmethod
    def generate(cls, pattern: Pattern, lat: float, lon: float, scale: float = 1.0) -> List[Coord]:
        """Dispatch to the correct generator."""
        generators = {
            Pattern.LOOP: cls.loop,
            Pattern.FIGURE_8: cls.figure_8,
            Pattern.STAR: cls.star,
            Pattern.SPIRAL: cls.spiral,
            Pattern.LOLLIPOP: cls.lollipop,
            Pattern.ZIGZAG: cls.zigzag,
        }
        fn = generators.get(pattern)
        if not fn:
            raise ValueError(f"Unknown pattern: {pattern}")
        return fn(lat, lon, scale)


class DistanceGenerator:
    """Generates routes targeting a specific distance."""

    @staticmethod
    def circular(lat: float, lon: float, distance_km: float, scale: float = 1.0) -> List[Coord]:
        """Generate a circular route approximating a target distance."""
        radius_km = distance_km / (2 * math.pi)
        radius_deg = (radius_km / 111.0) * scale
        pts = []
        n = 16
        for i in range(n + 1):
            angle = (i / n) * 2 * math.pi - math.pi / 2
            r_lon = radius_deg / math.cos(math.radians(lat))
            pts.append((
                lat + radius_deg * math.cos(angle),
                lon + r_lon * math.sin(angle)
            ))
        return pts


# ─── ROAD SNAPPING ────────────────────────────────────────────────────────────

class OSRMRouter:
    """Snaps geometric waypoints to real road network via OSRM."""

    BASE_URL = "https://router.project-osrm.org/route/v1/foot"

    @classmethod
    def snap(cls, waypoints: List[Coord]) -> List[Coord]:
        """
        Send waypoints to OSRM and return road-snapped coordinates.
        Falls back to straight-line if OSRM fails.
        """
        coords_str = ";".join(f"{lon},{lat}" for lat, lon in waypoints)
        url = f"{cls.BASE_URL}/{coords_str}?overview=full&geometries=geojson"

        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data.get("routes"):
                raw = data["routes"][0]["geometry"]["coordinates"]
                return [(lat, lon) for lon, lat in raw]
        except Exception as e:
            print(f"[OSRM] Warning: {e}. Falling back to raw waypoints.")

        return waypoints  # fallback


# ─── METRICS ─────────────────────────────────────────────────────────────────

def haversine_km(a: Coord, b: Coord) -> float:
    """Haversine distance between two lat/lon pairs in km."""
    R = 6371.0
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(h))


def total_distance_km(coords: List[Coord]) -> float:
    return sum(haversine_km(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def estimate_elevation_gain(distance_km: float, profile: ElevationProfile) -> int:
    """Rough elevation gain estimate based on profile."""
    gain_per_km = {
        ElevationProfile.FLAT: 8,
        ElevationProfile.MODERATE: 25,
        ElevationProfile.HILLY: 50,
        ElevationProfile.CHALLENGING: 90,
    }
    return round(distance_km * gain_per_km.get(profile, 8))


def estimate_time_min(distance_km: float, elevation_gain_m: int) -> int:
    """Estimate run time in minutes (Naismith's rule, ~6 min/km base pace)."""
    base_time = distance_km * 6.5
    elevation_penalty = elevation_gain_m / 10  # +1 min per 10m gain
    return round(base_time + elevation_penalty)


# ─── GPX EXPORT ───────────────────────────────────────────────────────────────

def coords_to_gpx(coords: List[Coord], name: str = "RunShape Route") -> str:
    """Convert coordinate list to GPX XML string."""
    trkpts = "\n".join(
        f'    <trkpt lat="{lat:.6f}" lon="{lon:.6f}"></trkpt>'
        for lat, lon in coords
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="RunShape" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata><name>{name}</name></metadata>
  <trk>
    <name>{name}</name>
    <trkseg>
{trkpts}
    </trkseg>
  </trk>
</gpx>"""


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

def generate_route(request: RouteRequest, snap_to_roads: bool = True) -> RouteResult:
    """
    Full route generation pipeline.

    1. Generate geometric waypoints
    2. Snap to road network (optional)
    3. Compute metrics
    4. Return structured result
    """
    # Step 1: Generate waypoints
    if request.mode == "pattern":
        if not request.pattern:
            raise ValueError("Pattern mode requires a pattern to be specified.")
        waypoints = PatternGenerator.generate(request.pattern, request.lat, request.lon, request.scale)
        pattern_label = request.pattern.value
    else:
        if not request.distance_km:
            raise ValueError("Distance mode requires distance_km to be specified.")
        waypoints = DistanceGenerator.circular(request.lat, request.lon, request.distance_km, request.scale)
        pattern_label = f"distance-{request.distance_km}km"

    # Step 2: Snap to roads
    coords = OSRMRouter.snap(waypoints) if snap_to_roads else waypoints

    # Step 3: Compute metrics
    dist_km = total_distance_km(coords)
    elev_gain = estimate_elevation_gain(dist_km, request.elevation)
    time_min = estimate_time_min(dist_km, elev_gain)

    # Step 4: GPX
    gpx = coords_to_gpx(coords, name=f"RunShape – {pattern_label}")

    return RouteResult(
        coordinates=coords,
        distance_km=round(dist_km, 2),
        elevation_gain_m=elev_gain,
        estimated_time_min=time_min,
        pattern_used=pattern_label,
        gpx=gpx,
    )


# ─── CLI / DEMO ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Demo: generate a figure-8 route in Brisbane CBD
    req = RouteRequest(
        lat=-27.4698,
        lon=153.0251,
        mode="pattern",
        pattern=Pattern.FIGURE_8,
        scale=1.0,
        elevation=ElevationProfile.FLAT,
    )
    result = generate_route(req, snap_to_roads=False)  # offline demo
    print(f"Pattern : {result.pattern_used}")
    print(f"Distance: {result.distance_km} km")
    print(f"Elev +  : {result.elevation_gain_m} m")
    print(f"Est Time: {result.estimated_time_min} min")
    print(f"Points  : {len(result.coordinates)}")
