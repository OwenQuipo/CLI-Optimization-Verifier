from __future__ import annotations

import argparse
import json
import os
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.version import version_metadata, version_string

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUNDLE_DIR = ROOT / "run_bundles"
DEFAULT_VERIFY_BIN = ROOT / "bin" / "verify"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def create_bundle(
    problem_path: Path,
    solution_path: Path,
    stdout: str,
    stderr: str,
    exit_code: int,
    origin: str,
    bundle_dir: Path = DEFAULT_BUNDLE_DIR,
    ui_version: Optional[str] = None,
    validation_warnings: Optional[list[str]] = None,
) -> Path:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    ts = _timestamp()
    bundle_name = f"{ts}_{origin}_{exit_code}_{uuid.uuid4().hex[:6]}"
    bundle_root = bundle_dir / bundle_name
    bundle_root.mkdir(parents=True, exist_ok=False)

    copied_problem = bundle_root / Path(problem_path).name
    copied_solution = bundle_root / Path(solution_path).name
    copied_problem.write_bytes(Path(problem_path).read_bytes())
    copied_solution.write_bytes(Path(solution_path).read_bytes())

    _write_file(bundle_root / "stdout.txt", stdout)
    _write_file(bundle_root / "stderr.txt", stderr)
    _write_file(bundle_root / "exit_code.txt", str(exit_code))

    meta = version_metadata(ui_version=ui_version)
    meta.update(
        {
            "timestamp": ts,
            "origin": origin,
            "problem": copied_problem.name,
            "solution": copied_solution.name,
            "exit_code": exit_code,
        }
    )
    if validation_warnings:
        meta["validation_warnings"] = validation_warnings
    _write_file(bundle_root / "metadata.json", json.dumps(meta, sort_keys=True, indent=2))

    archive_path = bundle_dir / f"{bundle_name}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(bundle_root, arcname=bundle_root.name)
    return archive_path


def run_and_bundle(
    problem_path: Path,
    solution_path: Path,
    verify_bin: Path = DEFAULT_VERIFY_BIN,
    bundle_dir: Path = DEFAULT_BUNDLE_DIR,
    origin: str = "cli",
    ui_version: Optional[str] = None,
) -> tuple[int, Path]:
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        stdout_path = Path(tmpdir) / "stdout.txt"
        stderr_path = Path(tmpdir) / "stderr.txt"
        with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
            result = subprocess.run(
                [str(verify_bin), str(problem_path), str(solution_path)],
                stdout=out,
                stderr=err,
                check=False,
                text=True,
            )
        stdout = stdout_path.read_text(encoding="utf-8")
        stderr = stderr_path.read_text(encoding="utf-8")
    archive = create_bundle(
        problem_path=problem_path,
        solution_path=solution_path,
        stdout=stdout,
        stderr=stderr,
        exit_code=result.returncode,
        origin=origin,
        bundle_dir=bundle_dir,
        ui_version=ui_version,
    )
    return result.returncode, archive


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CLI verifier and export a reproducible bundle.")
    parser.add_argument("problem", help="Path to problem JSON")
    parser.add_argument("solution", help="Path to solution JSON")
    parser.add_argument("--bundle-dir", default=str(DEFAULT_BUNDLE_DIR), help="Directory for bundle outputs")
    parser.add_argument("--verify-bin", default=str(DEFAULT_VERIFY_BIN), help="Path to verify executable")
    parser.add_argument("--origin", default="cli", help="Label for the run origin")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    problem = Path(args.problem).resolve()
    solution = Path(args.solution).resolve()
    bundle_dir = Path(args.bundle_dir).resolve()
    verify_bin = Path(args.verify_bin).resolve()
    exit_code, archive = run_and_bundle(
        problem_path=problem,
        solution_path=solution,
        verify_bin=verify_bin,
        bundle_dir=bundle_dir,
        origin=args.origin,
    )
    print(f"Bundle written to {archive} (exit={exit_code}, version={version_string()})")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
