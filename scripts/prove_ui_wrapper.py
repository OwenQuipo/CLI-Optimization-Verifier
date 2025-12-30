#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.request
from functools import partial
from http.server import HTTPServer
from pathlib import Path

from backend.server import ROOT, VERIFY_BIN, VerifyRequestHandler


def _start_server() -> tuple[HTTPServer, threading.Thread]:
    server = HTTPServer(("127.0.0.1", 0), partial(VerifyRequestHandler))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def main() -> int:
    problem = ROOT / "examples" / "problem.json"
    solution = ROOT / "examples" / "solution.json"
    cli = subprocess.run(
        [str(VERIFY_BIN), str(problem), str(solution)],
        capture_output=True,
        text=True,
        check=False,
    )

    server, thread = _start_server()
    try:
        url = f"http://{server.server_address[0]}:{server.server_address[1]}/verify"
        payload = json.dumps({"problem": problem.read_text(), "solution": solution.read_text()}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join()

    mismatches = []
    if body.get("exitCode") != cli.returncode:
        mismatches.append(f"exit code mismatch: ui={body.get('exitCode')} cli={cli.returncode}")
    if body.get("stdout") != cli.stdout:
        mismatches.append("stdout mismatch between UI and CLI")
    if body.get("stderr") != cli.stderr:
        mismatches.append("stderr mismatch between UI and CLI")

    if mismatches:
        for m in mismatches:
            sys.stderr.write(m + "\n")
        return 1

    print("UI wrapper matches CLI byte-for-byte (stdout/stderr/exit code)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
