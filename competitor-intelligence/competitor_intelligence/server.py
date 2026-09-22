from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import DB_PATH, HOST, PORT, WEBHOOK_TOKEN
from .service import IntelligenceService
from .store import Store


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class RequestHandler(BaseHTTPRequestHandler):
    service: IntelligenceService

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._static("index.html")
        if parsed.path in ("/sources", "/sources.html"):
            return self._static("sources.html")
        if parsed.path in ("/watchlist", "/watchlist.html"):
            return self._static("watchlist.html")
        if parsed.path == "/event" or parsed.path.startswith("/event/"):
            if parsed.path.endswith("/diff"):
                return self._static("diff.html")
            return self._static("event.html")
        if parsed.path.startswith("/static/"):
            return self._static(parsed.path.removeprefix("/static/"))
        if parsed.path == "/api/health":
            return self._json({"ok": True, "service": "competitor-intelligence"})
        if parsed.path == "/api/competitors":
            return self._json([item.to_dict() for item in self.service.competitors()])
        if parsed.path == "/api/monitors":
            return self._json(self.service.monitor_status())
        if parsed.path == "/api/watches":
            return self._json(self.service.watch_status())
        if parsed.path.startswith("/api/events/") and parsed.path.endswith("/diff"):
            event_id = parsed.path[len("/api/events/"):-len("/diff")].strip("/")
            evidence = self.service.event_diff(event_id)
            return self._json(evidence, HTTPStatus.OK) if evidence else self._json(
                {"detail": "Event evidence not found"}, HTTPStatus.NOT_FOUND)
        if parsed.path == "/api/events":
            query = parse_qs(parsed.query)
            filters = {key: values[0] for key, values in query.items() if values and values[0]}
            return self._json(self.service.events(filters))
        if parsed.path == "/api/summary":
            return self._json(self.service.summary())
        if parsed.path == "/api/source-health":
            return self._json(self.service.source_health())
        self._json({"detail": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
        except ValueError as exc:
            return self._json({"detail": str(exc)}, HTTPStatus.BAD_REQUEST)
        if parsed.path == "/api/webhooks/changedetection":
            if WEBHOOK_TOKEN and self.headers.get("X-Webhook-Token") != WEBHOOK_TOKEN:
                return self._json({"detail": "Invalid webhook token"}, HTTPStatus.UNAUTHORIZED)
            try:
                if isinstance(payload.get("competitor_ids"), list):
                    results = []
                    for competitor_id in payload["competitor_ids"]:
                        results.append(self.service.ingest_changedetection(
                            {**payload, "competitor_id": competitor_id}).to_dict())
                    return self._json(results, HTTPStatus.ACCEPTED)
                return self._json(self.service.ingest_changedetection(payload).to_dict(), HTTPStatus.ACCEPTED)
            except ValueError as exc:
                return self._json({"detail": str(exc)}, HTTPStatus.BAD_REQUEST)
        prefix = "/api/competitors/"
        watch_prefix = "/api/watches/"
        if parsed.path.startswith(watch_prefix) and parsed.path.endswith("/scan"):
            watch_id = parsed.path[len(watch_prefix):-len("/scan")].strip("/")
            watch = next((item for item in self.service.watches() if item.id == watch_id), None)
            return self._json(self.service.scan_watch(watch).to_dict()) if watch else self._json(
                {"detail": "Watch not found"}, HTTPStatus.NOT_FOUND)
        if parsed.path.startswith(prefix) and parsed.path.endswith("/scan"):
            competitor_id = parsed.path[len(prefix) : -len("/scan")].strip("/")
            return self._json(self.service.scan(competitor_id).to_dict())
        if parsed.path == "/api/scan-all":
            return self._json([result.to_dict() for result in self.service.scan_all()])
        if parsed.path == "/api/sync-changedetection":
            try:
                return self._json(self.service.sync_changedetection())
            except Exception as exc:
                return self._json({"detail": f"Changedetection sync failed: {exc}"}, HTTPStatus.BAD_GATEWAY)
        if parsed.path.startswith("/api/events/") and parsed.path.endswith("/analyze"):
            event_id = parsed.path[len("/api/events/"):-len("/analyze")].strip("/")
            try:
                analysis = self.service.analyze_event(event_id)
            except PermissionError as exc:
                return self._json({"detail": str(exc)}, HTTPStatus.TOO_MANY_REQUESTS)
            except ValueError as exc:
                return self._json({"detail": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
            except Exception as exc:
                return self._json({"detail": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return self._json(analysis) if analysis else self._json(
                {"detail": "Event evidence not found"}, HTTPStatus.NOT_FOUND)
        if parsed.path == "/api/poll-feeds":
            return self._json(self.service.poll_feeds())
        if parsed.path == "/api/search":
            query = str(payload.get("query", "")).strip()
            if not query:
                return self._json({"detail": "query is required"}, HTTPStatus.BAD_REQUEST)
            try:
                return self._json(self.service.search(query))
            except Exception as exc:
                return self._json({"detail": str(exc)}, HTTPStatus.BAD_GATEWAY)
        self._json({"detail": "Not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[competitor-intelligence] {self.address_string()} - {format % args}")

    def _static(self, relative_path: str) -> None:
        path = (STATIC_DIR / relative_path).resolve()
        if STATIC_DIR not in path.parents and path != STATIC_DIR:
            return self._json({"detail": "Not found"}, HTTPStatus.NOT_FOUND)
        if not path.exists() or not path.is_file():
            return self._json({"detail": "Not found"}, HTTPStatus.NOT_FOUND)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body must be valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("Request body must be a JSON object")
        return value

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def make_server(host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    store = Store(DB_PATH)
    service = IntelligenceService(store)

    class BoundHandler(RequestHandler):
        pass

    BoundHandler.service = service
    return ThreadingHTTPServer((host, port), BoundHandler)


def serve(host: str = HOST, port: int = PORT) -> None:
    server = make_server(host, port)
    print(f"JA Assure Competitor Intelligence listening at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping competitor intelligence service")
    finally:
        server.server_close()
