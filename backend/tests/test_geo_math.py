import math
import unittest


def round_coord(val: float, decimals: int = 6) -> float:
    return round(val, decimals)


def normalize_bearing(bearing: float) -> int:
    norm = round(((bearing % 360) + 360) % 360)
    return 0 if norm == 360 else norm


def destination_point(lat: float, lng: float, distance_meters: float, bearing_deg: float) -> tuple[float, float]:
    R = 6371000
    d_by_r = distance_meters / R
    lat_rad = math.radians(lat)
    lng_rad = math.radians(lng)
    bearing_rad = math.radians(bearing_deg)

    dest_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(d_by_r)
        + math.cos(lat_rad) * math.sin(d_by_r) * math.cos(bearing_rad)
    )

    dest_lng_rad = lng_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(d_by_r) * math.cos(lat_rad),
        math.cos(d_by_r) - math.sin(lat_rad) * math.sin(dest_lat_rad),
    )

    dest_lat = math.degrees(dest_lat_rad)
    dest_lng = ((math.degrees(dest_lng_rad) + 540) % 360) - 180

    return (round_coord(dest_lng, 6), round_coord(dest_lat, 6))


class TestGeoMath(unittest.TestCase):
    def test_normalize_bearing(self):
        self.assertEqual(normalize_bearing(0), 0)
        self.assertEqual(normalize_bearing(90), 90)
        self.assertEqual(normalize_bearing(360), 0)
        self.assertEqual(normalize_bearing(720), 0)
        self.assertEqual(normalize_bearing(-90), 270)
        self.assertEqual(normalize_bearing(450), 90)

    def test_destination_point_cardinal_directions(self):
        origin_lat, origin_lng = 43.125, 5.930
        dist = 200.0

        # Direction Nord (0°) -> la latitude augmente, longitude constante
        north_lng, north_lat = destination_point(origin_lat, origin_lng, dist, 0)
        self.assertGreater(north_lat, origin_lat)
        self.assertAlmostEqual(north_lng, origin_lng, places=4)

        # Direction Est (90°) -> la longitude augmente, latitude quasi constante
        east_lng, east_lat = destination_point(origin_lat, origin_lng, dist, 90)
        self.assertGreater(east_lng, origin_lng)
        self.assertAlmostEqual(east_lat, origin_lat, places=4)

        # Direction Sud (180°) -> la latitude diminue
        south_lng, south_lat = destination_point(origin_lat, origin_lng, dist, 180)
        self.assertLess(south_lat, origin_lat)

        # Direction Ouest (270°) -> la longitude diminue
        west_lng, west_lat = destination_point(origin_lat, origin_lng, dist, 270)
        self.assertLess(west_lng, origin_lng)


if __name__ == "__main__":
    unittest.main()
