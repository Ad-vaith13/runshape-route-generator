# 🏃 RunShape — Shape Your Run

> A data science tool that generates GPS running routes based on **geometric patterns** or **target distance**, snapped to real road networks.

![RunShape Demo](docs/demo.png)

---

## ✨ Features

| Mode | Description |
|---|---|
| **Pattern Mode** | Pick a shape (loop, figure-8, star, spiral, lollipop, zigzag) and the app generates a route that closely follows that pattern around your start point |
| **Distance Mode** | Set a target distance (1–42 km) and elevation profile; the app generates an optimised circular route matching your goal |

**Additional features:**
- 📍 GPS auto-location or manual address search (Nominatim geocoding)
- 🛣️ Road-snapped routes via OSRM (Open Source Routing Machine)
- 📊 Real-time stats: distance, elevation gain, estimated time
- ⬇️ GPX export (import into Garmin, Strava, Komoot, etc.)
- 🔗 Shareable route links

---

## 🗂️ Project Structure

```
runshape/
├── frontend/
│   └── index.html          # Single-file web app (Leaflet.js + vanilla JS)
├── backend/
│   ├── route_generator.py  # Core algorithms (patterns, metrics, GPX)
│   └── app.py              # Flask REST API
├── tests/
│   └── test_route_generator.py  # Pytest test suite
├── docs/
│   └── architecture.md     # System design notes
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Option A — Open the frontend directly (no server needed)

```bash
open frontend/index.html
```
The frontend calls the public OSRM API directly. No backend required for basic use.

### Option B — Run the full stack

**1. Clone and install:**
```bash
git clone https://github.com/your-username/runshape.git
cd runshape
pip install -r requirements.txt
```

**2. Start the API server:**
```bash
python backend/app.py
# → http://localhost:5000
```

**3. Open the app:**
```bash
open frontend/index.html
# or visit http://localhost:5000
```

---

## 🧠 How It Works

### Pattern Mode

Each pattern is defined as a mathematical function that takes a centre coordinate and scale factor, returning a list of `(lat, lon)` waypoints:

| Pattern | Algorithm |
|---|---|
| **Loop** | Parametric circle |
| **Figure-8** | Lemniscate of Bernoulli |
| **Star** | 5-pointed polar coordinates (alternating radii) |
| **Spiral** | Archimedean spiral (out + return) |
| **Lollipop** | Linear stem + circular head |
| **Zigzag** | Sawtooth wave, out and back |

### Distance Mode

Generates a circular route where the circumference matches the target distance:
```
radius = target_distance / (2π)
```
The scale slider multiplies the radius, letting you adjust the shape independently of the raw distance target.

### Road Snapping

Raw geometric waypoints are sent to [OSRM](https://project-osrm.org/) (foot profile), which returns road-network-aligned polylines. This ensures the route follows actual paths, streets, and footpaths.

### Metrics

| Metric | Method |
|---|---|
| Distance | Haversine formula over all consecutive coordinate pairs |
| Elevation gain | Lookup table (m/km) × route distance, scaled by elevation profile |
| Estimated time | Naismith's rule: 6.5 min/km base + 1 min per 10 m elevation |

---

## 📡 API Reference

### `POST /api/route`

Generate a route.

**Request body:**
```json
{
  "lat": -27.4698,
  "lon": 153.0251,
  "mode": "pattern",
  "pattern": "figure8",
  "scale": 1.0,
  "elevation": "flat",
  "snap": true
}
```

For distance mode:
```json
{
  "lat": -27.4698,
  "lon": 153.0251,
  "mode": "distance",
  "distance_km": 10.0,
  "scale": 1.0,
  "elevation": "moderate",
  "snap": true
}
```

**Response:**
```json
{
  "coordinates": [[-27.470, 153.025], ...],
  "distance_km": 9.8,
  "elevation_gain_m": 245,
  "estimated_time_min": 72,
  "pattern_used": "figure8",
  "gpx": "<?xml version..."
}
```

### `GET /api/patterns`

Returns list of available pattern IDs.

### `GET /api/health`

Health check.

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

The test suite covers:
- All 6 pattern generators (geometry validation, closure, scale effects)
- Distance generator (target accuracy within ±30%)
- Metric functions (haversine, elevation, time estimates)
- GPX export validity
- Full integration pipeline (no network required)

---

## 🔌 External Services

| Service | Purpose | Docs |
|---|---|---|
| [Nominatim](https://nominatim.openstreetmap.org/) | Address → coordinates geocoding | [API](https://nominatim.org/release-docs/latest/api/Search/) |
| [OSRM](https://project-osrm.org/) | Road-snapped routing (foot profile) | [API](http://project-osrm.org/docs/v5.5.1/api/) |
| [OpenStreetMap](https://www.openstreetmap.org/) | Map tiles | [Tile policy](https://operations.osmfoundation.org/policies/tiles/) |

All external services are **free and open**. No API keys required.

---

## 🗺️ Roadmap

- [ ] Elevation data integration (Open-Elevation API)
- [ ] Strava OAuth: auto-upload generated routes
- [ ] Custom waypoint snapping (click to pin points on map)
- [ ] Multi-day route planning
- [ ] Route history (localStorage / user accounts)
- [ ] Mobile PWA support

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first.

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m 'Add feature'`
4. Push: `git push origin feature/my-feature`
5. Open a pull request

---

## 📄 License

MIT © 2025 — RunShape contributors
