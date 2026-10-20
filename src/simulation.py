import random
from math import cos, radians
from pathlib import Path

import networkx as nx

from .models import Courier, Restaurant

DEFAULT_STANDARD_DEVIATION_METERS = 1200.0
_NON_DRIVABLE_HIGHWAYS = {
    "abandoned",
    "bridleway",
    "bus_guideway",
    "construction",
    "corridor",
    "cycleway",
    "elevator",
    "escalator",
    "footway",
    "no",
    "path",
    "pedestrian",
    "planned",
    "platform",
    "proposed",
    "raceway",
    "razed",
    "rest_area",
    "service",
    "services",
    "steps",
    "track",
}
_NON_DRIVABLE_SERVICE_TYPES = {
    "alley",
    "driveway",
    "emergency_access",
    "parking",
    "parking_aisle",
    "private",
}


def _tag_values(value: object) -> set[str]:
    if isinstance(value, (list, tuple, set)):
        return {str(item).casefold() for item in value}
    return {str(value).casefold()} if value is not None else set()


def _is_drivable_edge(attributes: dict[str, object]) -> bool:
    highway = _tag_values(attributes.get("highway"))
    if not highway or highway & _NON_DRIVABLE_HIGHWAYS:
        return False
    if "yes" in _tag_values(attributes.get("area")):
        return False
    if _tag_values(attributes.get("access")) & {"no", "private"}:
        return False
    if _tag_values(attributes.get("motor_vehicle")) & {"no"}:
        return False
    if _tag_values(attributes.get("motorcar")) & {"no"}:
        return False
    if _tag_values(attributes.get("service")) & _NON_DRIVABLE_SERVICE_TYPES:
        return False
    return True


def _retain_drivable_roads(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """remove arestas não viáveis do grafo"""
    filtered = graph.copy()
    filtered.remove_edges_from(
        [
            (start, end, key)
            for start, end, key, attributes in filtered.edges(
                keys=True, data=True
            )
            if not _is_drivable_edge(attributes)
        ]
    )
    filtered.remove_nodes_from(list(nx.isolates(filtered)))
    if filtered.number_of_edges() == 0:
        raise ValueError("o grafo das ruas esta vazio.")
    return filtered


def load_road_graph(
    graph_path: Path,
) -> nx.MultiDiGraph:
    """carrega o grafo viário de bh."""
    if not graph_path.is_file():
        raise FileNotFoundError(
            "A malha viária offline não foi encontrada em "
            f"'{graph_path}'. Coloque o grafo GraphML em data/roads/bh.graphml "
            "antes de usar a geração."
        )
    try:
        import osmnx as ox
    except ImportError as error:
        raise RuntimeError(
            "OSMnx é necessario pra rodar o projeto, instale as dependencias"
        ) from error

    graph = ox.io.load_graphml(graph_path)
    if len(graph) == 0:
        raise ValueError(f"Tho grafo das ruas esta vazio: {graph_path}")
    return _retain_drivable_roads(graph)


def generate_couriers(
    quantity: int,
    restaurants: list[Restaurant],
    road_graph: nx.MultiDiGraph,
    seed: int | None = None,
    standard_deviation_meters: float = DEFAULT_STANDARD_DEVIATION_METERS,
) -> list[Courier]:
    """Gera entregadores distribuídos aleatoriamente em torno dos restaurantes."""
    if quantity < 1:
        raise ValueError("insira pelo menos um entregador")
    if not restaurants:
        raise ValueError("insira pelo menos um restaurante")
    if standard_deviation_meters <= 0:
        raise ValueError("desvio padrão deve ser positivo")

    try:
        import osmnx as ox
    except ImportError as error:
        raise RuntimeError(
            "osmnx é necessário. Instale as dependencias"
        ) from error

    generator = random.Random(seed)
    ordered_centers = list(restaurants)
    generator.shuffle(ordered_centers)
    latitude_positions: list[float] = []
    longitude_positions: list[float] = []
    for index in range(quantity):
        center = ordered_centers[index % len(ordered_centers)]
        north_offset = generator.gauss(0, standard_deviation_meters)
        east_offset = generator.gauss(0, standard_deviation_meters)
        latitude_positions.append(center.latitude + north_offset / 110_574)
        longitude_positions.append(
            center.longitude
            + east_offset
            / (111_320 * max(abs(cos(radians(center.latitude))), 0.01))
        )

    nearest_nodes = ox.distance.nearest_nodes(
        road_graph,
        X=longitude_positions,
        Y=latitude_positions,
    )
    couriers: list[Courier] = []
    for index, node_id in enumerate(nearest_nodes, start=1):
        node = road_graph.nodes[node_id]
        couriers.append(
            Courier(
                courier_id=f"E{index:05d}",
                latitude=float(node["y"]),
                longitude=float(node["x"]),
            )
        )
    return couriers
