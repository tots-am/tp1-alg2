import gzip
import json
import unittest

import networkx as nx

from dashboard.service import DashboardService
from src.models import Restaurant


class DashboardServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.restaurants = [
            Restaurant(
                "restaurant-1",
                "Restaurante Central",
                "Restaurantes",
                "Rua Um, 10",
                "Centro",
                -19.9,
                -43.9,
            )
        ]
        self.graph = nx.MultiDiGraph()
        self.graph.graph["crs"] = "EPSG:4326"
        self.graph.add_node(1, x=-43.91, y=-19.91)
        self.graph.add_node(2, x=-43.89, y=-19.89)
        self.graph.add_edge(1, 2, highway="residential")
        self.service = DashboardService(self.restaurants, self.graph)

    def test_search_restaurants_finds_name_and_rejects_short_query(self) -> None:
        self.assertEqual(self.service.search_restaurants("r"), [])
        result = self.service.search_restaurants("central")
        self.assertEqual(result[0]["id"], "restaurant-1")

    def test_fleet_generation_and_nearby_search(self) -> None:
        fleet = self.service.generate_fleet(8)
        result = self.service.search_nearby("restaurant-1", 10)
        self.assertEqual(fleet["count"], 8)
        self.assertEqual(len(fleet["couriers"]), 8)
        self.assertEqual(len(result["matches"]), 8)
        self.assertEqual(result["restaurant"]["id"], "restaurant-1")

    def test_invalid_quantity_and_search_without_fleet_are_reported(self) -> None:
        with self.assertRaises(ValueError):
            self.service.generate_fleet(0)
        with self.assertRaisesRegex(ValueError, "Gere uma frota"):
            self.service.search_nearby("restaurant-1", 2)

    def test_map_data_is_gzip_compressed_and_contains_local_roads(self) -> None:
        payload = json.loads(gzip.decompress(self.service.compressed_map()))
        self.assertEqual(payload["bounds"], [-43.91, -19.91, -43.89, -19.89])
        self.assertEqual(payload["roads"], [[[-43.91, -19.91], [-43.89, -19.89]]])


if __name__ == "__main__":
    unittest.main()
