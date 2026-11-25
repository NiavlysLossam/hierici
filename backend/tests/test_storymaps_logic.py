import unittest
import unicodedata
import re


def slugify(value: str) -> str:
    """Normalise une chaîne pour créer un slug URL-friendly sans accents ni caractères spéciaux."""
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def validate_camera_bounds(lat: float, lng: float, zoom: float, bearing: float, pitch: float) -> tuple[bool, str | None]:
    if not (-90.0 <= lat <= 90.0):
        return False, "Latitude hors bornes [-90, 90]"
    if not (-180.0 <= lng <= 180.0):
        return False, "Longitude hors bornes [-180, 180]"
    if not (0.0 <= zoom <= 24.0):
        return False, "Zoom hors bornes [0, 24]"
    if not (0.0 <= bearing <= 360.0):
        return False, "Bearing hors bornes [0, 360]"
    if not (0.0 <= pitch <= 85.0):
        return False, "Pitch hors bornes [0, 85]"
    return True, None


def normalize_bearing(bearing: float) -> float:
    if bearing == 360.0:
        return 0.0
    return bearing % 360.0


class TestStorymapsLogic(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Histoire du Tramway 1886 !"), "histoire-du-tramway-1886")
        self.assertEqual(slugify("Épopée navale à Toulon"), "epopee-navale-a-toulon")
        self.assertEqual(slugify("   Espaces   Multiples---et-tirets   "), "espaces-multiples-et-tirets")
        self.assertEqual(slugify(""), "")

    def test_camera_bounds(self):
        valid, _ = validate_camera_bounds(43.12, 5.93, 14.0, 90.0, 45.0)
        self.assertTrue(valid)

        invalid_lat, err = validate_camera_bounds(95.0, 5.93, 14.0, 90.0, 45.0)
        self.assertFalse(invalid_lat)
        self.assertIn("Latitude", err)

        invalid_lng, err = validate_camera_bounds(43.12, 190.0, 14.0, 90.0, 45.0)
        self.assertFalse(invalid_lng)
        self.assertIn("Longitude", err)

        invalid_zoom, err = validate_camera_bounds(43.12, 5.93, -1.0, 90.0, 45.0)
        self.assertFalse(invalid_zoom)
        self.assertIn("Zoom", err)

        invalid_pitch, err = validate_camera_bounds(43.12, 5.93, 14.0, 90.0, 90.0)
        self.assertFalse(invalid_pitch)
        self.assertIn("Pitch", err)

    def test_normalize_bearing(self):
        self.assertEqual(normalize_bearing(360.0), 0.0)
        self.assertEqual(normalize_bearing(0.0), 0.0)
        self.assertEqual(normalize_bearing(180.0), 180.0)


if __name__ == "__main__":
    unittest.main()

