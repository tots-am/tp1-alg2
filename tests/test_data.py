import csv
import tempfile
import unittest
from pathlib import Path

from src.data import (
    load_prepared_restaurants,
    load_restaurants,
    save_prepared_restaurants,
)
from src.models import Restaurant


class RestaurantDataTests(unittest.TestCase):
    def test_loads_supported_cnaes_and_converts_utm_coordinates(self) -> None:
        columns = [
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
        ]
        rows = [
            {
                "ID_ATIV_ECON_ESTABELECIMENTO": "1",
                "CNAE_PRINCIPAL": "5611201",
                "DESCRICAO_CNAE_PRINCIPAL": "RESTAURANTES E SIMILARES",
                "DESC_LOGRADOURO": "RUA",
                "NOME_LOGRADOURO": "TESTE",
                "NUMERO_IMOVEL": "10",
                "NOME_BAIRRO": "CENTRO",
                "NOME": "NOME LEGAL",
                "NOME_FANTASIA": "*******",
                "GEOMETRIA": "POINT (609075.77 7805588.98)",
            },
            {
                "ID_ATIV_ECON_ESTABELECIMENTO": "2",
                "CNAE_PRINCIPAL": "5611204",
                "DESCRICAO_CNAE_PRINCIPAL": "BARES",
                "GEOMETRIA": "POINT (609075.77 7805588.98)",
            },
            {
                "ID_ATIV_ECON_ESTABELECIMENTO": "3",
                "CNAE_PRINCIPAL": "4711301",
                "DESCRICAO_CNAE_PRINCIPAL": "MERCADO",
                "GEOMETRIA": "POINT (609075.77 7805588.98)",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "sample.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns, delimiter=";")
                writer.writeheader()
                writer.writerows(rows)

            restaurants = load_restaurants(csv_path)

        self.assertEqual(
            {item.establishment_id for item in restaurants}, {"1", "2"}
        )
        restaurant = next(
            item for item in restaurants if item.establishment_id == "1"
        )
        self.assertAlmostEqual(restaurant.latitude, -19.9, delta=0.1)
        self.assertAlmostEqual(restaurant.longitude, -43.9, delta=0.1)
        self.assertEqual(restaurant.name, "NOME LEGAL")
        self.assertIn("nome legal", restaurant.search_text)
        self.assertEqual(restaurant.address, "RUA TESTE 10")

    def test_prepared_dataset_round_trip(self) -> None:
        original = RestaurantDataTests._restaurant_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "processed" / "restaurants.csv"
            save_prepared_restaurants([original], path)
            restored = load_prepared_restaurants(path)

        self.assertEqual(restored, [original])

    @staticmethod
    def _restaurant_fixture() -> Restaurant:
        return Restaurant(
            "123",
            "Restaurante Teste",
            "Restaurantes",
            "Rua Um, 10",
            "Centro",
            -19.9,
            -43.9,
            ("Nome Legal",),
        )


if __name__ == "__main__":
    unittest.main()
