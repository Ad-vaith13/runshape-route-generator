"""
RunShape - Flask API Server
============================
Exposes route generation as a REST API.
Run with: python app.py
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
from route_generator import (
    RouteRequest, Pattern, ElevationProfile, generate_route
)

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/route", methods=["POST"])
def create_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    try:
        req = RouteRequest(
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            mode=data.get("mode", "pattern"),
            pattern=Pattern(data["pattern"]) if data.get("pattern") else None,
            distance_km=float(data["distance_km"]) if data.get("distance_km") else None,
            scale=float(data.get("scale", 1.0)),
            elevation=ElevationProfile(data.get("elevation", "flat")),
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400

    try:
        result = generate_route(req, snap_to_roads=data.get("snap", True))
        return jsonify({
            "coordinates": result.coordinates,
            "distance_km": result.distance_km,
            "elevation_gain_m": result.elevation_gain_m,
            "estimated_time_min": result.estimated_time_min,
            "pattern_used": result.pattern_used,
            "gpx": result.gpx,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/patterns", methods=["GET"])
def list_patterns():
    return jsonify([p.value for p in Pattern])


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "RunShape"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
