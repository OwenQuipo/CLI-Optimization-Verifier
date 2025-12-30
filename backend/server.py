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

try:  # Optional dependency for schema validation
    import jsonschema
except Exception:  # pragma: no cover - optional
    jsonschema = None

from backend.draft_flow import draft_to_internal_json, translate_text_to_draft
from src.run_bundle import create_bundle
from src.version import version_metadata

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
VERIFY_BIN = ROOT / "bin" / "verify"
SCHEMAS_DIR = ROOT / "schemas"
UI_VERSION = os.environ.get("UI_VERSION", "ui-local")
SAVE_FAILURES = os.environ.get("VERIFY_SAVE_FAILURES", "0") == "1"


def _load_schema(name: str) -> dict[str, Any] | None:
    schema_path = SCHEMAS_DIR / name
    if not schema_path.exists():
        return None
    with schema_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


PROBLEM_SCHEMA = _load_schema("problem.schema.json")
SOLUTION_SCHEMA = _load_schema("solution.schema.json")


class VerifyRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self.path = "/frontend/index.html"
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/verify":
            self._handle_verify()
            return
        if self.path == "/draft":
            self._handle_draft()
            return
        if self.path == "/approve_and_verify":
            self._handle_approve_and_verify()
            return
        self.send_error(404, "Not found")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return  # Silence default stderr logging

    def _handle_draft(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        text = payload.get("text")
        if not isinstance(text, str):
            self._write_json({"error": "Field 'text' must be provided"}, status=400)
            return
        result = translate_text_to_draft(text)
        self._write_json(result, status=200)

    def _handle_approve_and_verify(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        draft = payload.get("structured_draft")
        run_options = payload.get("run_options") or {}
        if not isinstance(draft, dict):
            self._write_json({"error": "structured_draft must be an object"}, status=400)
            return
        problem_json, solution_json, warnings = draft_to_internal_json(draft)
        warning_dicts = [w.to_dict() for w in warnings]
        if any(w["severity"] == "error" for w in warning_dicts):
            self._write_json({"error": "Draft contains blocking errors", "warnings": warning_dicts}, status=400)
            return
        compare_solvers = bool(run_options.get("compare_solvers", False))
        response = self._run_verifier(problem_json, solution_json, compare_solvers=compare_solvers)
        response["internal_problem_json"] = problem_json
        response["internal_solution_json"] = solution_json
        if warning_dicts:
            response["warnings"] = warning_dicts
        self._write_json(response, status=200)

    def _handle_verify(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        problem_text = payload.get("problem")
        solution_text = payload.get("solution")
        if not isinstance(problem_text, str) or not isinstance(solution_text, str):
            self._write_json({"error": "Both 'problem' and 'solution' must be provided as strings"}, status=400)
            return
        response = self._run_verifier(problem_text, solution_text)
        self._write_json(response, status=200)

    def _run_verifier(self, problem_text: str, solution_text: str, compare_solvers: bool = False) -> dict[str, Any]:
        validation_warnings = self._validate_inputs(problem_text, solution_text)
        problem_path = None
        solution_path = None
        try:
            problem_fd, problem_path = tempfile.mkstemp(suffix=".json", text=True)
            solution_fd, solution_path = tempfile.mkstemp(suffix=".json", text=True)
            with os.fdopen(problem_fd, "w") as problem_file:
                problem_file.write(problem_text)
            with os.fdopen(solution_fd, "w") as solution_file:
                solution_file.write(solution_text)

            cmd = [str(VERIFY_BIN), problem_path, solution_path]
            if compare_solvers:
                cmd.append("--compare-solvers")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            response = {
                "exitCode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "version": version_metadata(ui_version=UI_VERSION),
            }
            if validation_warnings:
                response["validationWarnings"] = validation_warnings
            if SAVE_FAILURES and result.returncode != 0:
                try:
                    create_bundle(
                        problem_path=Path(problem_path),
                        solution_path=Path(solution_path),
                        stdout=result.stdout,
                        stderr=result.stderr,
                        exit_code=result.returncode,
                        origin="ui",
                        bundle_dir=ROOT / "failures",
                        ui_version=UI_VERSION,
                        validation_warnings=validation_warnings,
                    )
                except Exception:
                    pass  # Do not interfere with user-facing response
            return response
        finally:
            for path in (problem_path, solution_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def _validate_inputs(self, problem_text: str, solution_text: str) -> list[str]:
        warnings: list[str] = []
        if not jsonschema or not PROBLEM_SCHEMA or not SOLUTION_SCHEMA:
            return warnings
        warnings.extend(self._validate_one(problem_text, PROBLEM_SCHEMA, "problem.json"))
        warnings.extend(self._validate_one(solution_text, SOLUTION_SCHEMA, "solution.json"))
        return warnings

    def _validate_one(self, content: str, schema: dict[str, Any], label: str) -> list[str]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            return [f"{label}: invalid JSON ({exc})"]
        validator = jsonschema.Draft7Validator(schema)
        messages = []
        for error in validator.iter_errors(data):
            messages.append(f"{label}: {error.message}")
        return messages

    def _write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json_body(self) -> dict[str, Any] | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        try:
            body = self.rfile.read(content_length)
            return json.loads(body)
        except json.JSONDecodeError:
            self._write_json({"error": "Invalid JSON body"}, status=400)
        return None


def main() -> None:
    server_address = ("127.0.0.1", 8000)
    handler = partial(VerifyRequestHandler)
    httpd = HTTPServer(server_address, handler)
    print(f"Serving UI at http://{server_address[0]}:{server_address[1]}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
