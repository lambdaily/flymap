from __future__ import annotations

import json
import mimetypes
import os
import random
import re
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from fly_sim import run_indicator, run_survey
from pdf_report import build_report


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = ROOT / "data" / "indicators.json"
INDICATORS = json.loads(DATA.read_text(encoding="utf-8"))

FLY_NAMES = [
    "Ignacio Moscon",
    "Moscardo",
    "Mosquiel",
    "Moscardín",
    "Moscarina",
    "Mosquino",
    "Flyberto",
    "Moscaldo",
    "Moselia",
    "Moscencio",
    "Mosvaldo",
    "Mosilda",
    "Mosnesto",
    "Mosquino Jr.",
    "Moscardo de la Mancha",
    "Mosé Aurelio",
    "Mosferatu",
    "Mosco Polo",
    "Moscoberto",
    "Moscarda",
    "Mosquino Stardust",
    "Mosé Luis",
    "Moscarlota",
    "Moscovita",
    "Mosprano",
    "Mosquín",
    "Moscardín del Sur",
    "Mosberto",
    "Moscúlio",
    "Mosandra",
    "Moscarlo",
    "Mosquielito",
    "Mosé María",
    "Mosnuel",
    "Moscardo Azul",
    "Mosella",
    "Mosquiano",
    "Moscarina Luz",
    "Moscobardo",
    "Mosé Tomás",
    "Moscardo Volador",
    "Moscariño",
    "Mosvalentina",
    "Mosquimedes",
    "Moscarón",
    "Mosé Ignacio",
    "Moscarlín",
    "Mosabella",
    "Moscardo del Alba",
    "Mosquino Verde",
]
COUNTRIES = ["Paraguay", "México", "Colombia", "Argentina", "Uruguay", "Chile", "Perú", "Brasil"]


def generate_profile(seed: int | None = None) -> dict[str, str]:
    rng = random.Random(seed if seed is not None else time.time_ns())
    return {
        "name": rng.choice(FLY_NAMES),
        "country": rng.choice(COUNTRIES),
        "birthplace": "Moscú",
        "code": f"FM-{rng.randrange(1000, 9999)}",
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "FlyMap/0.1"

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_pdf(self, body: bytes, filename: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "service": "flymap", "backend": "surrogate-lif"})
            return
        if parsed.path == "/api/indicators":
            self.send_json({"indicators": INDICATORS})
            return
        if parsed.path == "/api/profile":
            self.send_json({"profile": generate_profile()})
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "JSON inválido"}, HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/simulate":
            indicator_id = payload.get("indicatorId")
            indicator = next((item for item in INDICATORS if item["id"] == indicator_id), None)
            if indicator is None:
                self.send_json({"error": "Indicador no encontrado"}, HTTPStatus.NOT_FOUND)
                return
            result = run_indicator(indicator, seed=int(payload.get("seed", 1)), steps=int(payload.get("steps", 36)))
            self.send_json(result)
            return

        if parsed.path == "/api/survey":
            self.send_json(run_survey(INDICATORS, seed=int(payload.get("seed", 1))))
            return

        if parsed.path == "/api/report":
            incoming_profile = payload.get("profile")
            profile = incoming_profile if isinstance(incoming_profile, dict) else generate_profile()
            incoming_results = payload.get("results") or {}
            results = incoming_results if isinstance(incoming_results, dict) else {}
            known_ids = {item["id"] for item in INDICATORS}
            clean_results = {key: value for key, value in results.items() if key in known_ids and isinstance(value, dict)}
            pdf = build_report(profile, INDICATORS, clean_results)
            slug = re.sub(r"[^a-z0-9]+", "-", str(profile.get("name", "flymap")).lower()).strip("-") or "flymap"
            self.send_pdf(pdf, f"flymap-{slug}.pdf")
            return

        self.send_json({"error": "Ruta no encontrada"}, HTTPStatus.NOT_FOUND)

    def serve_static(self, requested_path: str) -> None:
        relative = requested_path.lstrip("/") or "index.html"
        candidate = (STATIC / relative).resolve()
        if STATIC not in candidate.parents and candidate != STATIC:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not candidate.is_file():
            candidate = STATIC / "index.html"
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host, port = "0.0.0.0", int(os.environ.get("PORT", "8000"))
    print(f"FlyMap listo en http://{host}:{port}")
    try:
        ThreadingHTTPServer((host, port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido")


if __name__ == "__main__":
    main()
