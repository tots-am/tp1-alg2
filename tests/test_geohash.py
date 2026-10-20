import unittest

from src.geohash import decode_bounds, encode
from src.spatial_index import haversine_km


class GeohashTests(unittest.TestCase):
    def test_known_encoding_and_bounds(self) -> None:
        self.assertEqual(encode(42.6, -5.6, 5), "ezs42")
        south, north, west, east = decode_bounds("ezs42")
        self.assertLessEqual(south, 42.6)
        self.assertGreaterEqual(north, 42.6)
        self.assertLessEqual(west, -5.6)
        self.assertGreaterEqual(east, -5.6)

    def test_haversine_distance(self) -> None:
        self.assertAlmostEqual(
            haversine_km(-19.9167, -43.9345, -19.9167, -43.9345), 0
        )
        self.assertAlmostEqual(
            haversine_km(0, 0, 0, 1),
            111.195,
            delta=0.1,
        )


if __name__ == "__main__":
    unittest.main()
