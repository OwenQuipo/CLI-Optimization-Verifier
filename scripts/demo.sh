#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFY="${VERIFY_BIN:-$ROOT/bin/verify}"
EXAMPLES="$ROOT/examples"
BUNDLE_DIR="${BUNDLE_DIR:-$ROOT/demo_runs}"

mkdir -p "$BUNDLE_DIR"

echo "=== Feasible example ==="
"$VERIFY" "$EXAMPLES/problem.json" "$EXAMPLES/solution.json"
python -m src.run_bundle "$EXAMPLES/problem.json" "$EXAMPLES/solution.json" --bundle-dir "$BUNDLE_DIR" --origin demo-feasible

echo
echo "=== Infeasible example ==="
set +e
"$VERIFY" "$EXAMPLES/problem.json" "$EXAMPLES/infeasible_solution.json"
set -e
python -m src.run_bundle "$EXAMPLES/problem.json" "$EXAMPLES/infeasible_solution.json" --bundle-dir "$BUNDLE_DIR" --origin demo-infeasible

echo
echo "Bundles written to $BUNDLE_DIR"
