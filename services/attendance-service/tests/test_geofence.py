import pytest
from app.utils.geofence import geofence_check, calculate_distance

def test_circle_inside():
    r=geofence_check(6.9271,79.8612,"circle",{"center":{"lat":6.9271,"lng":79.8612},"radius_m":50})
    assert r["inside"] is True and r["distance_meters"] <= 50

def test_circle_outside():
    r=geofence_check(6.9285,79.8612,"circle",{"center":{"lat":6.9271,"lng":79.8612},"radius_m":50})
    assert r["inside"] is False

def test_square_points_inside():
    square={"points":[[6.9270,79.8610],[6.9270,79.8620],[6.9280,79.8620],[6.9280,79.8610]]}
    assert geofence_check(6.9275,79.8615,"polygon",square)["inside"] is True

def test_square_vertices_outside():
    square={"vertices":[[6.9270,79.8610],[6.9270,79.8620],[6.9280,79.8620],[6.9280,79.8610]]}
    assert geofence_check(6.9290,79.8630,"polygon",square)["inside"] is False

def test_invalid_coordinates():
    with pytest.raises(ValueError):
        calculate_distance(100,0,0,0)

def test_unordered_quad_vertices_inside():
    # Simulates row-ordered vertices (TL, TR, BL, BR) that would form a bowtie polygon if not ordered
    quad = {"vertices": [[6.795559, 79.900916], [6.795543, 79.901272], [6.795141, 79.900866], [6.795111, 79.901216]]}
    # Center of this venue
    res = geofence_check(6.795335, 79.901094, "polygon", quad)
    assert res["inside"] is True
    assert res["distance_meters"] is not None and res["distance_meters"] < 30.0
