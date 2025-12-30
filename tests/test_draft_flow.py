import json
import subprocess
import tempfile
import threading
import urllib.request
from functools import partial
from http.server import HTTPServer
from pathlib import Path

from backend.draft_flow import draft_to_internal_json, translate_text_to_draft
from backend.server import VERIFY_BIN, VerifyRequestHandler


def _start_server():
    server = HTTPServer(("127.0.0.1", 0), partial(VerifyRequestHandler))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post(server, path, payload):
    url = f"http://{server.server_address[0]}:{server.server_address[1]}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_draft_to_json_blocks_missing_assignment():
    draft = {
        "variables": [{"id": "x1"}],
        "objective": {"sense": "min", "linear_terms": [{"var": "x1", "coeff": 1}], "quadratic_terms": []},
        "constraints": [],
        "candidate_solution": [],
        "metadata": {},
    }
    problem_json, solution_json, warnings = draft_to_internal_json(draft)
    assert problem_json == ""
    assert solution_json == ""
    assert any(w.severity == "error" for w in warnings)


def test_text_to_draft_approve_and_verify_matches_cli():
    text = """
    Variables: x1, x2, x3
    Objective: minimize 1 x1 + 2 x2 + 2 x3 -1 x2*x3
    Constraints:
      cap-1: x1 + x2 <= 2
      min-cover: -x2 - x3 <= -1
    Proposed solution: x1=1, x2=1, x3=1
    """
    translation = translate_text_to_draft(text)
    assert translation["structured_draft"]
    assert translation["needs_clarification"] is False

    draft = translation["structured_draft"]
    problem_json, solution_json, warnings = draft_to_internal_json(draft)
    assert not any(w.severity == "error" for w in warnings)

    # CLI baseline using generated JSON
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as pfile:
        pfile.write(problem_json)
        problem_path = pfile.name
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as sfile:
        sfile.write(solution_json)
        solution_path = sfile.name

    cli = subprocess.run(
        [str(VERIFY_BIN), str(problem_path), str(solution_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    server, thread = _start_server()
    try:
        body = _post(server, "/approve_and_verify", {"structured_draft": draft})
    finally:
        server.shutdown()
        thread.join()
        Path(problem_path).unlink(missing_ok=True)
        Path(solution_path).unlink(missing_ok=True)

    assert body["exitCode"] == cli.returncode
    assert body["stdout"] == cli.stdout
    assert body["stderr"] == cli.stderr
