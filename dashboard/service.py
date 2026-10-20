from __future__ import annotations

import gzip
import json
import threading
import time
from typing import Any

import networkx as nx
from pyproj import CRS, Transformer

from src.models import Courier, Restaurant
from src.simulation import generate_couriers
from src.spatial_index import CourierSpatialIndex

AVERAGE_SPEED_KMH = 20.0
MAX_COURIERS = 5000


class DashboardService:
    def __init__(
        self,
        restaurants: list[Restaurant],
        road_graph: nx.MultiDiGraph,
        graph_error: str | None = None,
    ) -> None:
        self.restaurants = restaurants
        self.road_graph = road_graph
        self.graph_error = graph_error
        self.couriers: list[Courier] = []
        self.index = CourierSpatialIndex()
        self._lock = threading.RLock()
        self._compressed_map: bytes | None = None

    def health(self) -> dict[str, int | bool | str | None]:
        return {
            "ok": True,
            "restaurants": len(self.restaurants),
            "road_nodes": self.road_graph.number_of_nodes(),
            "road_edges": self.road_graph.number_of_edges(),
            "couriers": len(self.couriers),
            "graph_error": self.graph_error,
        }

    def search_restaurants(self, query: str, limit: int = 100) -> list[dict[str, str]]:
        normalized_query = query.strip().casefold()
        if len(normalized_query) < 2:
            return []
        return [
            {
                "id": restaurant.establishment_id,
                "label": restaurant.label,
                "name": restaurant.name,
            }
            for restaurant in self.restaurants
            if normalized_query in restaurant.search_text
        ][:limit]

    def generate_fleet(self, quantity: int) -> dict[str, Any]:
        if not 1 <= quantity <= MAX_COURIERS:
            raise ValueError(f"A quantidade deve estar entre 1 e {MAX_COURIERS}.")
        with self._lock:
            self.couriers = []
            self.index.rebuild([])
            couriers = generate_couriers(quantity, self.restaurants, self.road_graph)
            self.couriers = couriers
            self.index.rebuild(couriers)
            return {
                "count": len(couriers),
                "couriers": [
                    {
                        "id": courier.courier_id,
                        "latitude": courier.latitude,
                        "longitude": courier.longitude,
                    }
                    for courier in couriers
                ],
            }

    def search_nearby(
        self, establishment_id: str, radius_km: float
    ) -> dict[str, Any]:
        if not 0.2 <= radius_km <= 10:
            raise ValueError("O raio deve estar entre 0,2 e 10 km.")
        restaurant = next(
            (
                item
                for item in self.restaurants
                if item.establishment_id == establishment_id
            ),
            None,
        )
        if restaurant is None:
            raise ValueError("O estabelecimento selecionado não foi encontrado.")
        with self._lock:
            if not self.couriers:
                raise ValueError("Gere uma frota antes de realizar a busca.")
            started_at = time.perf_counter()
            matches, candidate_count = self.index.search_nearby(
                restaurant.latitude, restaurant.longitude, radius_km
            )
            elapsed_ms = (time.perf_counter() - started_at) * 1000
        return {
            "restaurant": {
                "id": restaurant.establishment_id,
                "name": restaurant.name,
                "address": restaurant.address,
                "neighborhood": restaurant.neighborhood,
                "latitude": restaurant.latitude,
                "longitude": restaurant.longitude,
            },
            "radius_km": radius_km,
            "candidate_count": candidate_count,
            "elapsed_ms": elapsed_ms,
            "matches": [
                {
                    "id": item.courier.courier_id,
                    "latitude": item.courier.latitude,
                    "longitude": item.courier.longitude,
                    "distance_km": item.distance_km,
                    "eta_minutes": item.eta_minutes(AVERAGE_SPEED_KMH),
                }
                for item in matches
            ],
        }

    def compressed_map(self) -> bytes:
        with self._lock:
            if self._compressed_map is not None:
                return self._compressed_map
            graph_crs = CRS.from_user_input(
                self.road_graph.graph.get("crs", "EPSG:4326")
            )
            transformer = (
                Transformer.from_crs(graph_crs, "EPSG:4326", always_xy=True)
                if not graph_crs.is_geographic
                else None
            )
            roads: list[list[list[float]]] = []
            min_longitude = min_latitude = float("inf")
            max_longitude = max_latitude = float("-inf")
            for start, end, attributes in self.road_graph.edges(data=True):
                geometry = attributes.get("geometry")
                if geometry is not None and hasattr(geometry, "coords"):
                    coordinates = geometry.coords
                else:
                    coordinates = (
                        (
                            self.road_graph.nodes[start]["x"],
                            self.road_graph.nodes[start]["y"],
                        ),
                        (
                            self.road_graph.nodes[end]["x"],
                            self.road_graph.nodes[end]["y"],
                        ),
                    )
                path: list[list[float]] = []
                for x, y in coordinates:
                    longitude, latitude = (
                        transformer.transform(float(x), float(y))
                        if transformer
                        else (float(x), float(y))
                    )
                    longitude, latitude = float(longitude), float(latitude)
                    path.append([longitude, latitude])
                    min_longitude = min(min_longitude, longitude)
                    max_longitude = max(max_longitude, longitude)
                    min_latitude = min(min_latitude, latitude)
                    max_latitude = max(max_latitude, latitude)
                if len(path) > 1:
                    roads.append(path)
            payload = {
                "roads": roads,
                "bounds": (
                    [
                        min_longitude,
                        min_latitude,
                        max_longitude,
                        max_latitude,
                    ]
                    if roads
                    else None
                ),
            }
            self._compressed_map = gzip.compress(
                json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                compresslevel=6,
            )
            return self._compressed_map
