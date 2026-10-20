"""Implementação do geohash para indexar as coordenadas geográficas no espaço"""
from math import ceil, cos, radians

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_VALUES = {character: value for value, character in enumerate(BASE32)}
_WORLD = (-90.0, 90.0, -180.0, 180.0)
MAX_PRECISION = 8


def encode(latitude: float, longitude: float, precision: int = MAX_PRECISION) -> str:
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude deve estar entre -90 e 90 graus")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude deve estar entre -180 e 180 graus")
    if not 1 <= precision <= MAX_PRECISION:
        raise ValueError(f"Precision deve estar entre 1 e {MAX_PRECISION}")

    lat_min, lat_max, lon_min, lon_max = _WORLD
    result: list[str] = []
    value = 0
    bits_used = 0
    longitude_turn = True

    while len(result) < precision:
        if longitude_turn:
            midpoint = (lon_min + lon_max) / 2
            if longitude >= midpoint:
                value = (value << 1) | 1
                lon_min = midpoint
            else:
                value <<= 1
                lon_max = midpoint
        else:
            midpoint = (lat_min + lat_max) / 2
            if latitude >= midpoint:
                value = (value << 1) | 1
                lat_min = midpoint
            else:
                value <<= 1
                lat_max = midpoint

        longitude_turn = not longitude_turn
        bits_used += 1
        if bits_used == 5:
            result.append(BASE32[value])
            value = 0
            bits_used = 0

    return "".join(result)


def decode_bounds(geohash: str) -> tuple[float, float, float, float]:
    if not geohash:
        raise ValueError("O geohash não pode ser vazio")

    lat_min, lat_max, lon_min, lon_max = _WORLD
    longitude_turn = True
    for character in geohash.casefold():
        try:
            value = _BASE32_VALUES[character]
        except KeyError as error:
            raise ValueError(f"caractere inválido no geohash: {character!r}.") from error

        for bit in (16, 8, 4, 2, 1):
            if longitude_turn:
                midpoint = (lon_min + lon_max) / 2
                if value & bit:
                    lon_min = midpoint
                else:
                    lon_max = midpoint
            else:
                midpoint = (lat_min + lat_max) / 2
                if value & bit:
                    lat_min = midpoint
                else:
                    lat_max = midpoint
            longitude_turn = not longitude_turn

    return lat_min, lat_max, lon_min, lon_max


def covering_prefixes(
    latitude: float,
    longitude: float,
    radius_km: float,
    precision: int = 5,
) -> set[str]:
    """Retorna os prefixos das células que estao dento de um circulo"""
    if radius_km < 0:
        raise ValueError("raio não pode ser negativo")
    if not 1 <= precision <= MAX_PRECISION:
        raise ValueError(f"Precision deve estar entre 1 e {MAX_PRECISION}")

    center = encode(latitude, longitude, precision)
    lat_min, lat_max, lon_min, lon_max = decode_bounds(center)
    cell_latitude = (lat_min + lat_max) / 2
    cell_longitude = (lon_min + lon_max) / 2
    latitude_step = lat_max - lat_min
    longitude_step = lon_max - lon_min

    latitude_radius = radius_km / 110.574
    longitude_radius = radius_km / max(
        111.320 * cos(radians(latitude)), 0.01
    )
    row_count = ceil(latitude_radius / latitude_step) + 1
    column_count = ceil(longitude_radius / longitude_step) + 1

    prefixes: set[str] = set()
    for row in range(-row_count, row_count + 1):
        neighbor_latitude = cell_latitude + row * latitude_step
        if not -90 <= neighbor_latitude <= 90:
            continue
        for column in range(-column_count, column_count + 1):
            neighbor_longitude = cell_longitude + column * longitude_step
            neighbor_longitude = (neighbor_longitude + 180) % 360 - 180
            prefixes.add(
                encode(neighbor_latitude, neighbor_longitude, precision)
            )
    return prefixes
