# RunShape — Architecture Notes

## System Overview

```
┌─────────────────────────────────────────────────────┐
│                   Browser (User)                     │
│  ┌──────────────┐        ┌───────────────────────┐  │
│  │  Sidebar UI  │──────→ │   Leaflet.js Map       │  │
│  │  (controls)  │←────── │   (route display)      │  │
│  └──────────────┘        └───────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │  HTTP (optional, for Flask API)
         ┌───────────┴──────────────┐
         │     Flask API (app.py)   │
         │  POST /api/route         │
         └───────────┬──────────────┘
                     │  Python function calls
         ┌───────────┴──────────────┐
         │  route_generator.py      │
         │  ├── PatternGenerator    │
         │  ├── DistanceGenerator   │
         │  ├── OSRMRouter          │
         │  └── Metrics / GPX       │
         └───────────┬──────────────┘
                     │  HTTP (road snapping)
         ┌───────────┴──────────────┐
         │  External APIs           │
         │  ├── OSRM (routing)      │
         │  ├── Nominatim (geocode) │
         │  └── OSM Tiles (map)     │
         └──────────────────────────┘
```

## Data Flow

### Pattern Mode
1. User picks pattern + location → JS generates geometric `(lat, lon)` waypoints
2. Waypoints sent to OSRM `/route/v1/foot/{coords}` → road-snapped polyline returned
3. Polyline drawn on Leaflet map; metrics computed client-side

### Distance Mode
1. User sets km target + elevation → JS computes circle radius from `r = d / 2π`
2. Circle sampled as 16 waypoints → OSRM snapping → draw + metrics

## Key Design Decisions

### Why OSRM over Google Maps?
- Free with no API key required
- Open-source, self-hostable
- Foot routing profile respects footpaths and pedestrian zones

### Why no elevation API by default?
- Open-Elevation API has rate limits; SRTM data is ~90 m resolution
- Current elevation estimates are intentionally simple (m/km lookup tables)
- Accurate elevation requires async requests per-point → slower UX

### Frontend as single HTML file
- Zero build tooling, instant deployment anywhere (GitHub Pages, Netlify, S3)
- All map and routing logic is client-side; backend is optional

## Extension Points

| Feature | Where to add |
|---|---|
| New pattern | Add entry to `PATTERNS` array in `index.html` + method in `PatternGenerator` |
| Real elevation | Replace `estimate_elevation_gain()` with Open-Elevation API call |
| Strava upload | Add OAuth flow in `app.py`, POST GPX to Strava API `/uploads` |
| User accounts | Add SQLite + Flask-Login to `app.py`, store routes per user |
