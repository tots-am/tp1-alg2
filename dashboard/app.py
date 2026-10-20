from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import networkx as nx

from src.data import load_prepared_restaurants
from src.simulation import load_road_graph

from .service import DashboardService

ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = Path(__file__).resolve().parent / "web"
RESTAURANTS_PATH = ROOT / "data" / "processed" / "restaurants.csv"
ROAD_GRAPH_PATH = ROOT / "data" / "roads" / "bh.graphml"
DEFAULT_PORT = 8765
MAX_REQUEST_BYTES = 1024 * 1024


class DashboardRequestHandler(BaseHTTPRequestHandler):
    service: DashboardService

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/api/health":
            self._send_json(self.service.health())
        elif parsed.path == "/api/restaurants":
            query = parse_qs(parsed.query).get("q", [""])[0]
            self._send_json({"restaurants": self.service.search_restaurants(query)})
        elif parsed.path == "/api/map":
            self._send_gzip_json(self.service.compressed_map())
        elif parsed.path in ("/", "/index.html", "/style.css", "/app.js"):
            self._send_static(parsed.path)
        else:
            self._send_json({"error": "Rota não encontrada."}, status=404)

    def do_POST(self) -> None:
        if self.path not in ("/api/fleet", "/api/search"):
            self._send_json({"error": "Rota não encontrada."}, status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > MAX_REQUEST_BYTES:
                raise ValueError("Tamanho de requisição inválido.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("O corpo da requisição deve ser um objeto JSON.")
            if self.path == "/api/fleet":
                quantity = payload.get("quantity")
                if isinstance(quantity, bool) or not isinstance(quantity, int):
                    raise ValueError("A quantidade de entregadores deve ser inteira.")
                result = self.service.generate_fleet(quantity)
            else:
                establishment_id = payload.get("establishment_id")
                radius_km = payload.get("radius_km")
                if not isinstance(establishment_id, str):
                    raise ValueError("Selecione um estabelecimento para a busca.")
                if isinstance(radius_km, bool) or not isinstance(
                    radius_km, (float, int)
                ):
                    raise ValueError("Informe um raio numérico.")
                result = self.service.search_nearby(
                    establishment_id, float(radius_km)
                )
            self._send_json(result)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            self._send_json({"error": str(error)}, status=400)
        except (OSError, RuntimeError) as error:
            self._send_json({"error": str(error)}, status=500)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_gzip_json(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, request_path: str) -> None:
        filename = "index.html" if request_path == "/" else request_path[1:]
        file_path = STATIC_ROOT / filename
        if not file_path.is_file() or file_path.parent != STATIC_ROOT:
            self._send_json({"error": "Arquivo não encontrado."}, status=404)
            return
        body = file_path.read_bytes()
        content_type, _ = mimetypes.guess_type(file_path.name)
        if file_path.suffix == ".js":
            content_type = "text/javascript"
        self.send_response(200)
        self.send_header(
            "Content-Type", f"{content_type or 'application/octet-stream'}; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


class LocalDashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, address: tuple[str, int], service: DashboardService
    ) -> None:
        handler = type(
            "BoundDashboardRequestHandler",
            (DashboardRequestHandler,),
            {"service": service},
        )
        super().__init__(address, handler)


def load_service() -> tuple[DashboardService, str | None]:
    restaurants = load_prepared_restaurants(RESTAURANTS_PATH)
    try:
        road_graph = load_road_graph(ROAD_GRAPH_PATH)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as error:
        road_graph = nx.MultiDiGraph()
        return DashboardService(restaurants, road_graph, str(error)), str(error)
    return DashboardService(restaurants, road_graph), None


def main() -> None:
    service, graph_error = load_service()
    try:
        server = LocalDashboardServer(("127.0.0.1", DEFAULT_PORT), service)
    except OSError:
        server = LocalDashboardServer(("127.0.0.1", 0), service)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    if graph_error:
        print(f"Aviso: {graph_error}")
    print(f"Dashboard local iniciado em {url}")
    print("Pressione Ctrl+C nesta janela para encerrar.")
    threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando o dashboard...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
