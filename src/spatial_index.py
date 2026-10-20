from dataclasses import dataclass, field
from math import asin, cos, radians, sin, sqrt

from .geohash import MAX_PRECISION, covering_prefixes, encode
from .models import Courier, NearbyCourier
from .trie import RadixTrie

EARTH_RADIUS_KM = 6371.0088
SEARCH_PRECISION = 5


def haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    lat_a, lat_b = radians(latitude_a), radians(latitude_b)
    delta_latitude = lat_b - lat_a
    delta_longitude = radians(longitude_b - longitude_a)
    haversine = (
        sin(delta_latitude / 2) ** 2
        + cos(lat_a) * cos(lat_b) * sin(delta_longitude / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(min(1.0, haversine)))


@dataclass(slots=True)
class CourierSpatialIndex:
    precision: int = MAX_PRECISION
    _trie: RadixTrie[Courier] = field(init=False, repr=False)
    _couriers: list[Courier] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not 1 <= self.precision <= MAX_PRECISION:
            raise ValueError(
                f"precicion deve ser entre 1 e {MAX_PRECISION}."
            )
        self._trie: RadixTrie[Courier] = RadixTrie()
        self._couriers: list[Courier] = []

    def rebuild(self, couriers: list[Courier]) -> None:
        self._trie.clear()
        self._couriers = list(couriers)
        for courier in self._couriers:
            self._trie.insert(
                encode(courier.latitude, courier.longitude, self.precision),
                courier,
            )

    def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> tuple[list[NearbyCourier], int]:
        if radius_km < 0:
            raise ValueError("raio de busca não pode ser negativo")

        prefixes = covering_prefixes(
            latitude,
            longitude,
            radius_km,
            min(SEARCH_PRECISION, self.precision),
        )
        candidates_by_id: dict[str, Courier] = {}
        for prefix in prefixes:
            for courier in self._trie.search_prefix(prefix):
                candidates_by_id[courier.courier_id] = courier

        nearby: list[NearbyCourier] = []
        for courier in candidates_by_id.values():
            distance = haversine_km(
                latitude, longitude, courier.latitude, courier.longitude
            )
            if distance <= radius_km:
                nearby.append(NearbyCourier(courier, distance))
        nearby.sort(key=lambda result: (result.distance_km, result.courier.courier_id))
        return nearby, len(candidates_by_id)

    @property
    def couriers(self) -> list[Courier]:
        return list(self._couriers)
