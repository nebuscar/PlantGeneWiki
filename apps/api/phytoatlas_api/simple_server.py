"""Dependency-free HTTP server for PhytoAtlas graph queries.

This server is intended for environments where FastAPI is not installed yet.
It exposes the same minimal graph endpoints using Python's standard library.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .graph_store import GraphStoreError, SQLiteGraphStore


def int_query(query: dict[str, list[str]], name: str, default: int, upper: int) -> int:
    try:
        value = int(query.get(name, [str(default)])[0])
    except ValueError:
        value = default
    return max(0, min(value, upper))


def neighbor_query_options(query: dict[str, list[str]]) -> dict[str, object]:
    return {
        "direction": query.get("direction", ["both"])[0],
        "predicate": query.get("predicate", [None])[0],
        "exclude_predicates": tuple(query.get("exclude_predicate", [])),
        "limit": int_query(query, "limit", 50, 500),
    }


class PhytoAtlasHandler(BaseHTTPRequestHandler):
    store = SQLiteGraphStore()

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            if path == "/api/health":
                self.send_json({"status": "ok"})
                return

            if path == "/api/graph/summary":
                self.send_json(self.store.get_summary())
                return

            if path == "/api/graph/search":
                q = query.get("q", [""])[0]
                if not q:
                    self.send_json({"detail": "Missing q"}, status=400)
                    return
                result = self.store.search_nodes(
                    q,
                    object_type=query.get("object_type", [None])[0],
                    species_id=query.get("species_id", [None])[0],
                    limit=int_query(query, "limit", 20, 100),
                )
                self.send_json({"query": q, "count": len(result), "nodes": result})
                return

            species_prefix = "/api/graph/species/"
            if path.startswith(species_prefix) and path.endswith("/genes"):
                species_id = unquote(path[len(species_prefix) : -len("/genes")])
                self.send_json(
                    self.store.list_species_genes(
                        species_id,
                        limit=int_query(query, "limit", 50, 500),
                        offset=int_query(query, "offset", 0, 10_000_000),
                    )
                )
                return

            neighbors_prefix = "/api/graph/neighbors/"
            if path.startswith(neighbors_prefix):
                node_id = unquote(path[len(neighbors_prefix) :])
                result = self.store.get_neighbors(node_id, **neighbor_query_options(query))
                if result["node"] is None:
                    self.send_json({"detail": f"Node not found: {node_id}"}, status=404)
                    return
                self.send_json(result)
                return

            node_prefix = "/api/graph/nodes/"
            if path.startswith(node_prefix):
                node_id = unquote(path[len(node_prefix) :])
                node = self.store.get_node(node_id)
                if node is None:
                    self.send_json({"detail": f"Node not found: {node_id}"}, status=404)
                    return
                self.send_json(node)
                return

            self.send_json({"detail": "Not found"}, status=404)
        except GraphStoreError as exc:
            self.send_json({"detail": str(exc)}, status=503)
        except Exception as exc:  # pragma: no cover
            self.send_json({"detail": f"Internal server error: {exc}"}, status=500)

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--database", default=None)
    args = parser.parse_args()

    if args.database:
        PhytoAtlasHandler.store = SQLiteGraphStore(args.database)

    server = ThreadingHTTPServer((args.host, args.port), PhytoAtlasHandler)
    print(f"PhytoAtlas API listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
