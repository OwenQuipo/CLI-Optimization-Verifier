CLI-first optimization verification tool (binary QUBO-style)

What this delivers
- Deterministic verifier for binary decision vectors under linear/quadratic objectives.
- Single command: `verify problem.json solution.json`.
- Outputs: feasibility with violations, objective value, best-known comparator (if provided), gap estimate (never claims optimal), variable sensitivity ranking, optional solver comparison (deterministic seed).

Directory structure
```
.
├── README.md                  # Design and execution plan
├── bin/
│   └── verify                 # CLI entry (Python/Go/Node wrapper; single binary later)
├── src/
│   ├── cli.py                 # Argument parsing, execution flow orchestration
│   ├── models.py              # Core data models (Problem, Solution, Constraint, Objective, RunResult)
│   ├── parser.py              # Load/validate JSON into models using schemas
│   ├── feasibility.py         # Constraint checks and violation reporting
│   ├── objective.py           # Objective evaluation (linear + quadratic terms)
│   ├── sensitivity.py         # Local sensitivity via bit flips
│   ├── comparator.py          # Best-known handling and gap computation
│   ├── solvers.py             # Minimal internal solvers (greedy, deterministic anneal, brute if small)
│   ├── reporting.py           # Deterministic formatting of CLI output
│   └── utils/
│       └── determinism.py     # Seed control, numeric tolerances
├── schemas/
│   ├── problem.schema.json    # JSON Schema for problem definitions
│   └── solution.schema.json   # JSON Schema for candidate solutions
├── tests/
│   ├── test_parser.py         # Schema validation, model loading
│   ├── test_feasibility.py    # Constraint handling and violation outputs
│   ├── test_objective.py      # Objective evaluation correctness
│   ├── test_sensitivity.py    # Determinism of sensitivity ranking
│   └── test_cli.py            # End-to-end run with fixtures
└── examples/
    ├── problem.json           # Sample problem for smoke testing
    └── solution.json          # Sample candidate solution
```

Core data models (Python-style structs; any language equivalent is fine)
- `Problem`: `variables` (list of ids), `linear` (map var->coefficient), `quadratic` (map (i,j)->coefficient with i<=j), `constraints` (list of `Constraint`), `best_known` (optional objective value + label), `metadata` (source, units).
- `Constraint`: `lhs` terms (map var->coefficient), `sense` (<=, ==, >=), `rhs` (number), `label`.
- `Solution`: `assignment` (map var->0/1), `label` (source of candidate), `metadata`.
- `ObjectiveResult`: `value` (number), `components` (linear sum, quadratic sum).
- `FeasibilityResult`: `status` (feasible/infeasible/unknown), `violations` (list of {label, amount}).
- `SensitivityEntry`: `var`, `delta` (objective change on flip), `feasible_after_flip` (bool).
- `RunResult`: aggregates feasibility, objective result, gap, sensitivity ranking, solver comparison summary.

Strict execution flow for `verify problem.json solution.json`
1) Load: parse JSON files, validate against schemas, and map into models; fail fast on schema errors.
2) Pre-check: ensure binary domains, matching variable sets, deterministic seed setup.
3) Feasibility: evaluate constraints; if any violation, mark infeasible and list violations (do not compute sensitivity if infeasible).
4) Objective: compute linear + quadratic objective value exactly.
5) Comparator: if `best_known` provided, compute gap = (candidate - best_known)/abs(best_known); mark "unknown" if best_known missing.
6) Sensitivity: for each variable, flip bit (one-at-a-time), recompute objective and feasibility; rank by absolute delta (feasible flips only reported by default).
7) Optional solver comparison (flag-gated): run deterministic greedy; if problem size below threshold, run brute force; deterministic anneal with fixed seed; compare objective values and feasibility status.
8) Reporting: render plain-text report with sections: input summary, feasibility/violations, objective value, comparator/gap, sensitivity ranking, solver comparison; exit codes: 0 feasible, 1 infeasible, 2 error/unknown.

Modules and responsibilities (v0.1)
- `cli.py`: CLI args, flag handling (`--compare-solvers`, `--max-brute-size`), wiring modules, exit codes.
- `parser.py`: JSON loading, schema validation, type/shape checks, ordering of variables.
- `models.py`: Dataclasses/structs; simple container logic only.
- `feasibility.py`: Constraint evaluation with numeric tolerance; violation calculation.
- `objective.py`: Deterministic objective computation; enforces symmetric quadratic handling.
- `sensitivity.py`: Bit-flip analysis; optionally limited to top-k variables; deterministic ordering ties broken by variable id.
- `comparator.py`: Best-known extraction, gap computation; handles absent comparator as "unknown".
- `solvers.py`: Minimal deterministic solvers; guarded by size thresholds; no randomness beyond fixed seed.
- `reporting.py`: Stable, line-based output; no ANSI; deterministic ordering.
- `utils/determinism.py`: Seed control, tolerance constants, shared helpers.

Boundaries (not in v0.1)
- No mixed-integer or continuous variables; binary only.
- No non-linear constraints; only linear constraints with scalar rhs.
- No stochastic outputs; no external solver APIs; no remote calls.
- No parallelism or distributed runs.
- No web/UI components; CLI only.
- No automatic best-known lookup; comparator must be provided in problem file.
- No probabilistic statements; never claim optimality unless brute proves it.

Example full run (plain text)
```
$ verify examples/problem.json examples/solution.json
Input: vars=3, constraints=2, candidate=greedy-v1
Feasibility: feasible
Violations: none
Objective:
  linear=5.0
  quadratic=-1.0
  total=4.0
Comparator:
  best_known: 3.5 (label=paper-A)
  gap: 14.29% worse
Sensitivity (best 3 flips):
  x1 flip -> +2.0 (feasible)
  x2 flip -> -1.0 (feasible)
  x3 flip -> +0.5 (feasible)
Solver comparison (deterministic):
  greedy: 4.0
  brute: 3.5 (size=3^2=9 evaluated)
Exit code: 0
```

Sample fixtures
- `examples/problem.json`: 3-variable QUBO with two linear constraints and a provided best-known objective.
- `examples/solution.json`: candidate assignment labeled `greedy-v1` for smoke testing.

How to run
- Install Python 3.10+.
- Make sure the entrypoint is executable: `chmod +x bin/verify`.
- Run: `./bin/verify examples/problem.json examples/solution.json`.
- Optional flags (once implemented in CLI):
  - `--compare-solvers` to run deterministic greedy/brute/anneal.
  - `--max-brute-size` to cap brute-force search space (default 4096 states).
- Exit codes: 0 feasible, 1 infeasible, 2 error.

Encoding constraints (v0.1)
- `linear_eq`: sum(lhs_i * x_i) == rhs (tolerance 1e-9)
- `linear_ineq`: sum(lhs_i * x_i) <= rhs (tolerance 1e-9). Encode >= by multiplying both sides by -1 to fit <= form.
- `at_most_k`: sum(lhs_i * x_i) <= rhs (same semantics as linear_ineq; use when coefficients are 1s and rhs is k).
- `xor`: sum(lhs_i * x_i) == 1
