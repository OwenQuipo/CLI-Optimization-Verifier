#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
VERIFY_BIN = ROOT / "bin" / "verify"


class VerifyRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self.path = "/frontend/index.html"
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/verify":
            self.send_error(404, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        try:
            body = self.rfile.read(content_length)
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._write_json({"error": "Invalid JSON body"}, status=400)
            return

        problem_text = payload.get("problem")
        solution_text = payload.get("solution")
        if not isinstance(problem_text, str) or not isinstance(solution_text, str):
            self._write_json({"error": "Both 'problem' and 'solution' must be provided as strings"}, status=400)
            return

        problem_path = None
        solution_path = None
        try:
            problem_fd, problem_path = tempfile.mkstemp(suffix=".json", text=True)
            solution_fd, solution_path = tempfile.mkstemp(suffix=".json", text=True)
            with os.fdopen(problem_fd, "w") as problem_file:
                problem_file.write(problem_text)
            with os.fdopen(solution_fd, "w") as solution_file:
                solution_file.write(solution_text)

            result = subprocess.run(
                [str(VERIFY_BIN), problem_path, solution_path],
                capture_output=True,
                text=True,
                check=False,
            )
            response = {
                "exitCode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            self._write_json(response, status=200)
        except Exception as exc:  # pragma: no cover - defensive
            self._write_json({"error": str(exc)}, status=500)
        finally:
            for path in (problem_path, solution_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return  # Silence default stderr logging

    def _write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    server_address = ("127.0.0.1", 8000)
    handler = partial(VerifyRequestHandler)
    httpd = HTTPServer(server_address, handler)
    print(f"Serving UI at http://{server_address[0]}:{server_address[1]}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
