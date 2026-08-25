from __future__ import annotations

import math
from typing import Any

EARTH_RADIUS_M = 6_371_000.0


def validate_coordinates(latitude: float, longitude: float) -> None:
    if not (-90 <= latitude <= 90):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180 <= longitude <= 180):
        raise ValueError("longitude must be between -180 and 180")


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return EARTH_RADIUS_M * 2 * math.asin(math.sqrt(min(1.0, a)))


def _point(item: Any) -> tuple[float, float]:
    if isinstance(item, dict):
        lat = item.get("lat", item.get("latitude"))
        lon = item.get("lng", item.get("lon", item.get("longitude")))
        if lat is None or lon is None:
            raise ValueError("Invalid geofence point")
        return float(lat), float(lon)
    if isinstance(item, (list, tuple)) and len(item) == 2:
        return float(item[0]), float(item[1])
    raise ValueError("Invalid geofence point")


def _extract_circle(boundary: dict) -> tuple[float, float, float]:
    center = boundary.get("center")
    if center:
        lat, lon = _point(center)
    else:
        lat = boundary.get("latitude", boundary.get("lat"))
        lon = boundary.get("longitude", boundary.get("lng", boundary.get("lon")))
        if lat is None or lon is None:
            raise ValueError("Circle geofence requires center coordinates")
        lat, lon = float(lat), float(lon)
    radius = boundary.get("radius_m", boundary.get("radius", boundary.get("radius_meters")))
    if radius is None or float(radius) <= 0:
        raise ValueError("Circle geofence requires a positive radius")
    return lat, lon, float(radius)


def _extract_vertices(boundary: dict) -> list[tuple[float, float]]:
    raw = boundary.get("vertices", boundary.get("points", boundary.get("coordinates")))
    if isinstance(raw, dict) and "coordinates" in raw:
        raw = raw["coordinates"]
    if not isinstance(raw, list) or len(raw) < 4:
        raise ValueError("Polygon/square geofence requires at least 4 vertices")
    return [_point(x) for x in raw]


def point_in_polygon(latitude: float, longitude: float, vertices: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(vertices) - 1
    for i, (yi, xi) in enumerate(vertices):
        yj, xj = vertices[j]
        intersects = ((xi > longitude) != (xj > longitude)) and (
            latitude < (yj - yi) * (longitude - xi) / ((xj - xi) or 1e-15) + yi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def geofence_check(latitude: float, longitude: float, shape_type: str, boundary_data: dict) -> dict:
    validate_coordinates(latitude, longitude)
    shape = (shape_type or "circle").lower()
    if shape == "circle":
        center_lat, center_lon, radius = _extract_circle(boundary_data)
        distance = calculate_distance(latitude, longitude, center_lat, center_lon)
        return {"inside": distance <= radius, "distance_meters": distance, "boundary": {"type": "circle", "radius_m": radius}}

    # DB uses `polygon`; four vertices are treated as a square for the current implementation.
    vertices = _extract_vertices(boundary_data)
    return {
        "inside": point_in_polygon(latitude, longitude, vertices),
        "distance_meters": None,
        "boundary": {"type": "square" if len(vertices) == 4 else "polygon", "vertices": vertices},
    }
