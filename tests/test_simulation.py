import unittest
from pathlib import Path

import networkx as nx

from src.models import Restaurant
from src.simulation import (
    _is_drivable_edge,
    _retain_drivable_roads,
    generate_couriers
)
class CourierSimulationTests(unittest.TestCase):
    def test_generates_requested_count_on_demand_centered_road_nodes(self) -> None:
        restaurants = [
            Restaurant("1", "Centro 1", "", "", "", -19.9, -43.9),
            Restaurant("2", "Centro 2", "", "", "", -20.9, -42.9),
        ]
        graph = nx.MultiDiGraph()
        graph.graph["crs"] = "EPSG:4326"
        graph.add_node(1, x=-43.9, y=-19.9)
        graph.add_node(2, x=-42.9, y=-20.9)

        couriers = generate_couriers(8, restaurants, graph, seed=42)

        self.assertEqual(len(couriers), 8)
        self.assertEqual(
            [item.courier_id for item in couriers],
            [f"E{index:05d}" for index in range(1, 9)],
        )
        self.assertEqual(
            {(item.latitude, item.longitude) for item in couriers},
            {(-19.9, -43.9), (-20.9, -42.9)},
        )
        self.assertEqual(
            sum(item.latitude == -19.9 for item in couriers), 4
        )

    def test_local_graph_excludes_walkways_and_keeps_drivable_roads(self) -> None:
        graph = nx.MultiDiGraph()
        graph.add_edge(1, 2, highway="residential")
        graph.add_edge(2, 3, highway="footway")
        graph.add_edge(3, 4, highway="service", service="driveway")
        graph.add_edge(4, 5, highway="secondary", access="private")
        graph.add_edge(6, 7, name="missing highway tag")

        filtered = _retain_drivable_roads(graph)

        self.assertEqual(list(filtered.edges()), [(1, 2)])
        self.assertEqual(set(filtered.nodes), {1, 2})
        self.assertTrue(_is_drivable_edge({"highway": "primary"}))
        self.assertFalse(_is_drivable_edge({"highway": "steps"}))


if __name__ == "__main__":
    unittest.main()
