import json
import subprocess
import threading
import urllib.request
from functools import partial
from http.server import HTTPServer
from pathlib import Path
import tempfile

from backend.server import ROOT, VERIFY_BIN, VerifyRequestHandler


def _start_server():
    server = HTTPServer(("127.0.0.1", 0), partial(VerifyRequestHandler))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post_verify(server, problem_text, solution_text):
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/verify"
    payload = json.dumps({"problem": problem_text, "solution": solution_text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_ui_matches_cli_byte_for_byte():
    problem_path = ROOT / "examples" / "problem.json"
    solution_path = ROOT / "examples" / "solution.json"

    cli = subprocess.run(
        [str(VERIFY_BIN), str(problem_path), str(solution_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    server, thread = _start_server()
    try:
        body = _post_verify(server, problem_path.read_text(), solution_path.read_text())
    finally:
        server.shutdown()
        thread.join()

    assert body["exitCode"] == cli.returncode
    assert body["stdout"] == cli.stdout
    assert body["stderr"] == cli.stderr


def test_ui_maps_cli_errors():
    problem_path = ROOT / "examples" / "problem.json"
    bad_solution = '{"assignment": {"x1": 1}}'  # missing other variables, invalid schema

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        tmp.write(bad_solution)
        bad_solution_path = tmp.name

    cli = subprocess.run(
        [str(VERIFY_BIN), str(problem_path), bad_solution_path],
        capture_output=True,
        text=True,
        check=False,
    )
    server, thread = _start_server()
    try:
        body = _post_verify(server, problem_path.read_text(), bad_solution)
    finally:
        server.shutdown()
        thread.join()
        Path(bad_solution_path).unlink(missing_ok=True)

    assert body["exitCode"] == cli.returncode
    assert body["stdout"] == cli.stdout
    assert body["stderr"] == cli.stderr
