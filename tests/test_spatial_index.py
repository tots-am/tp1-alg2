import unittest

from src.models import Courier
from src.spatial_index import CourierSpatialIndex


class SpatialIndexTests(unittest.TestCase):
    def test_search_includes_neighbors_and_filters_exact_radius(self) -> None:
        origin = Courier("E1", -19.9167, -43.9345)
        nearby = Courier("E2", -19.9200, -43.9300)
        distant = Courier("E3", -19.9500, -43.9345)
        index = CourierSpatialIndex()
        index.rebuild([origin, nearby, distant])

        matches, candidates = index.search_nearby(-19.9167, -43.9345, 1.0)

        self.assertEqual([item.courier.courier_id for item in matches], ["E1", "E2"])
        self.assertGreaterEqual(candidates, len(matches))
        self.assertEqual(len(index.couriers), 3)

    def test_rebuild_discards_previous_fleet(self) -> None:
        index = CourierSpatialIndex()
        index.rebuild([Courier("old", -19.9167, -43.9345)])
        index.rebuild([Courier("new", -19.9167, -43.9345)])

        matches, _ = index.search_nearby(-19.9167, -43.9345, 1)
        self.assertEqual([item.courier.courier_id for item in matches], ["new"])

    def test_search_works_when_index_precision_is_shorter_than_prefix_default(self) -> None:
        index = CourierSpatialIndex(precision=3)
        index.rebuild([Courier("short", -19.9167, -43.9345)])

        matches, _ = index.search_nearby(-19.9167, -43.9345, 1)

        self.assertEqual([item.courier.courier_id for item in matches], ["short"])


if __name__ == "__main__":
    unittest.main()
