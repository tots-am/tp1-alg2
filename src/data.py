import csv
import json
import re
from pathlib import Path

from pyproj import Transformer

from .models import Restaurant

_POINT_PATTERN = re.compile(
    r"^\s*POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)\s*$",
    re.IGNORECASE,
)
_RESTAURANT_AND_BAR_CNAES = {"5611201", "5611204", "5611205"}


def load_restaurants(csv_path: Path) -> list[Restaurant]:
    """Carrega restaurantes e bares do dataset csv"""
    transformer = Transformer.from_crs(
        "EPSG:31983", "EPSG:4326", always_xy=True
    )
    restaurants: list[Restaurant] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        required_columns = {
            "ID_ATIV_ECON_ESTABELECIMENTO",
            "CNAE_PRINCIPAL",
            "DESCRICAO_CNAE_PRINCIPAL",
            "DESC_LOGRADOURO",
            "NOME_LOGRADOURO",
            "NUMERO_IMOVEL",
            "NOME_BAIRRO",
            "NOME",
            "NOME_FANTASIA",
            "GEOMETRIA",
        }
        missing = required_columns.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"csv esta sem colunas: {', '.join(sorted(missing))}."
            )

        for row in reader:
            cnae = (row.get("CNAE_PRINCIPAL") or "").strip()
            if cnae not in _RESTAURANT_AND_BAR_CNAES:
                continue
            geometry = _POINT_PATTERN.match(row.get("GEOMETRIA") or "")
            if geometry is None:
                continue

            east, north = float(geometry.group(1)), float(geometry.group(2))
            longitude, latitude = transformer.transform(east, north)
            if not -20.2 <= latitude <= -19.5 or not -44.5 <= longitude <= -43.5:
                continue

            street = " ".join(
                part
                for part in (
                    (row.get("DESC_LOGRADOURO") or "").strip(),
                    (row.get("NOME_LOGRADOURO") or "").strip(),
                )
                if part
            )
            number = (row.get("NUMERO_IMOVEL") or "").strip()
            address = " ".join(part for part in (street, number) if part)
            legal_name = (row.get("NOME") or "").strip()
            fantasy_name = (row.get("NOME_FANTASIA") or "").strip()
            if not any(character.isalnum() for character in legal_name):
                legal_name = ""
            if not any(character.isalnum() for character in fantasy_name):
                fantasy_name = ""
            restaurants.append(
                Restaurant(
                    establishment_id=(
                        row["ID_ATIV_ECON_ESTABELECIMENTO"].strip()
                    ),
                    name=fantasy_name or legal_name or "Estabelecimento sem nome",
                    cnae_description=(
                        row.get("DESCRICAO_CNAE_PRINCIPAL") or ""
                    ).strip(),
                    address=address,
                    neighborhood=(row.get("NOME_BAIRRO") or "").strip(),
                    latitude=latitude,
                    longitude=longitude,
                    aliases=tuple(
                        name
                        for name in (
                            legal_name,
                            fantasy_name,
                        )
                        if name
                    ),
                )
            )

    if not restaurants:
        raise ValueError(
            "Nenhum restaurante ou bar com coordenadas de bh foi achado."
        )
    restaurants.sort(key=lambda item: (item.name.casefold(), item.establishment_id))
    return restaurants


def save_prepared_restaurants(
    restaurants: list[Restaurant], csv_path: Path
) -> None:
    """Salva o dataset filtrado e com coordenadas convertidas"""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "establishment_id",
        "name",
        "cnae_description",
        "address",
        "neighborhood",
        "latitude",
        "longitude",
        "aliases",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=columns)
        writer.writeheader()
        for item in restaurants:
            writer.writerow(
                {
                    "establishment_id": item.establishment_id,
                    "name": item.name,
                    "cnae_description": item.cnae_description,
                    "address": item.address,
                    "neighborhood": item.neighborhood,
                    "latitude": item.latitude,
                    "longitude": item.longitude,
                    "aliases": json.dumps(item.aliases, ensure_ascii=False),
                }
            )


def load_prepared_restaurants(csv_path: Path) -> list[Restaurant]:
    """Carrega o dataset sem requerer transformação de coordenadas e filtragem de CNAE"""
    restaurants: list[Restaurant] = []
    with csv_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required_columns = {
            "establishment_id",
            "name",
            "cnae_description",
            "address",
            "neighborhood",
            "latitude",
            "longitude",
            "aliases",
        }
        missing = required_columns.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"csv esta faltando colunas:: {', '.join(sorted(missing))}."
            )
        for row in reader:
            aliases = json.loads(row["aliases"])
            if not isinstance(aliases, list) or not all(
                isinstance(alias, str) for alias in aliases
            ):
                raise ValueError("nomes inválidos no dataset")
            restaurants.append(
                Restaurant(
                    establishment_id=row["establishment_id"],
                    name=row["name"],
                    cnae_description=row["cnae_description"],
                    address=row["address"],
                    neighborhood=row["neighborhood"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    aliases=tuple(aliases),
                )
            )
    if not restaurants:
        raise ValueError("dataset está vazio")
    return restaurants
