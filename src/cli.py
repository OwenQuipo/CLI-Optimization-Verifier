from __future__ import annotations

import argparse
import sys

from src.comparator import compute_gap, get_best_known
from src.feasibility import check_feasibility
from src.models import RunResult
from src.objective import evaluate_objective
from src.parser import ParseError, load_problem, load_solution
from src.reporting import render_report
from src.sensitivity import sensitivity_analysis
from src.solvers import brute_force_solver, deterministic_anneal, greedy_solver
from src.utils.determinism import set_seed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify binary QUBO solutions.")
    parser.add_argument("problem", help="Path to problem JSON")
    parser.add_argument("solution", help="Path to solution JSON")
    parser.add_argument(
        "--compare-solvers",
        action="store_true",
        help="Run deterministic internal solvers for comparison",
    )
    parser.add_argument(
        "--max-brute-size",
        type=int,
        default=4096,
        help="Maximum states for brute force (2^n); skips if exceeded",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    set_seed(0)
    try:
        problem = load_problem(args.problem)
        solution = load_solution(args.solution, problem)
    except ParseError as exc:
        sys.stderr.write(f"Parse error: {exc}\n")
        return 2
    except Exception as exc:  # pragma: no cover - safety net
        sys.stderr.write(f"Unexpected error loading inputs: {exc}\n")
        return 2

    feasibility = check_feasibility(problem.constraints, solution.assignment)
    objective = evaluate_objective(problem, solution)
    best_known = get_best_known(problem)
    gap = compute_gap(objective.total, best_known)

    sensitivity = []
    if feasibility.status == "feasible":
        sensitivity = sensitivity_analysis(problem, solution, objective.total)

    solver_comparison = {}
    if args.compare_solvers:
        solver_comparison["greedy"] = greedy_solver(problem)
        solver_comparison["brute"] = brute_force_solver(problem, args.max_brute_size)
        solver_comparison["anneal"] = deterministic_anneal(problem)

    run_result = RunResult(
        feasibility=feasibility,
        objective=objective,
        gap=gap,
        best_known=best_known,
        sensitivity=sensitivity,
        solver_comparison=solver_comparison,
    )

    report = render_report(problem, solution, run_result)
    sys.stdout.write(report + "\n")

    if feasibility.status == "feasible":
        return 0
    if feasibility.status == "infeasible":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
