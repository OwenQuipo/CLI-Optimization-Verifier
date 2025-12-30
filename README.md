CLI-first verification tool for binary QUBO problems with an approval-gated UI

What this delivers
- Deterministic CLI: `verify problem.json solution.json` (CLI is the source of truth).
- UI with two flows: Tab A “Verify JSON” (unchanged) and Tab B “Draft from Text” (text → structured draft → user edits → explicit “Approve & Verify”).
- Outputs: feasibility with violations, objective value, optional best-known comparator and gap, sensitivity ranking, optional solver comparison (deterministic seed). stdout/stderr shown verbatim; exit codes respected.

Directory structure (key paths)
```
.
├── bin/verify               # CLI entrypoint
├── backend/
│   ├── server.py            # Serves frontend; endpoints /verify, /draft, /approve_and_verify
│   └── draft_flow.py        # Text→draft translator, draft validation, deterministic draft→JSON
├── frontend/
│   ├── index.html           # Two-tab UI (Verify JSON / Draft from Text)
│   ├── main.js              # Draft editor, warnings, approval gate, verify calls
│   └── style.css            # UI styling
├── schemas/
│   ├── problem.schema.json  # Problem schema
│   └── solution.schema.json # Solution schema
├── src/                     # CLI internals (parser, objective, feasibility, solvers, reporting, etc.)
└── tests/                   # Pytest suite (CLI, UI parity, draft flow)
```

Workflows
- CLI: `./bin/verify <problem.json> <solution.json>` → exit 0 feasible, 1 infeasible, 2 error.
- UI Tab A (Verify JSON): paste/upload problem.json and solution.json (or load example) → “Verify” → runs CLI unchanged.
- UI Tab B (Draft from Text):
  1) Enter natural language → “Draft Structured Problem (unverified)” (no verification yet).
  2) Review structured draft (variables, objective, constraints, proposed solution) with warnings banner. Errors block approval; warnings list all assumptions.
  3) Edit via form fields (no JSON editing). Clarification questions shown if translator is unsure.
  4) Click “Approve Structure & Verify” → backend validates draft, builds internal JSON, runs CLI, returns stdout/stderr/exit code. Optional compare-solvers toggle.
  5) Optional: download internal JSON (clearly labeled) after approval.

Data contracts (UI ↔ backend)
- structured_draft: {variables:[{id,label?}], objective:{sense:"min"|"max", linear_terms:[{var,coeff}], quadratic_terms:[{var_i,var_j,coeff}]}, constraints:[{label?,sense:"<="|"=="|">=",terms:[{var,coeff}],rhs:number}], candidate_solution:[{var,value:0|1}], metadata:{source_text_hash,draft_version,created_at}}
- warnings: {code, message, severity:"info"|"warn"|"error", field_path?, assumption?}
- translation_result: {structured_draft, warnings, needs_clarification:boolean, clarification_questions?:[]}

Backend endpoints
- POST /verify: {problem:string, solution:string} → {stdout, stderr, exitCode, version, validationWarnings?}
- POST /draft: {text:string} → translation_result (no verification).
- POST /approve_and_verify: {structured_draft, run_options?:{compare_solvers?:bool}} → {stdout, stderr, exitCode, warnings?, internal_problem_json?, internal_solution_json?, version}

Deterministic draft→JSON rules
- Validate variables unique; candidate_solution values in {0,1}; constraints senses in {<=,==,>=}. Errors block verify.
- Variable ordering preserved for problem variables and solution assignment.
- Max objective negates coefficients (info warning); >= constraints normalized to <= (info warning). Unknown variable references or missing assignments are blocking errors.

How to run
- Env: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- CLI: `chmod +x bin/verify` then `./bin/verify examples/problem.json examples/solution.json` (flags: `--compare-solvers`, `--max-brute-size`).
- UI: `python backend/server.py` → open http://127.0.0.1:8000/ → use Tab A or Tab B as described.
- Failure capture: set `VERIFY_SAVE_FAILURES=1` when running the UI server to archive non-zero runs in `failures/`.
- Version stamping: `./bin/verify --print-version` for CLI-only; UI shows CLI/UI versions in footer.

Tests
- All tests: `.venv/bin/python -m pytest`
- UI/CLI parity: `tests/test_ui_equivalence.py` ensures /verify matches CLI output.
- Draft flow: `tests/test_draft_flow.py` covers draft validation and text→draft→approve→verify round-trip.
