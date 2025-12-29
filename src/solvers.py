from __future__ import annotations

import itertools
from typing import Dict, Optional

from src.feasibility import check_feasibility
from src.models import Problem, Solution
from src.objective import evaluate_objective
from src.utils.determinism import set_seed


def greedy_solver(problem: Problem) -> Optional[float]:
    assignment: Dict[str, int] = {v: 0 for v in problem.variables}
    # Single pass: flip if objective improves and remains feasible.
    for var in problem.variables:
        current_solution = Solution(assignment=assignment, label="greedy-current")
        current_obj = evaluate_objective(problem, current_solution).total
        flipped_assignment = dict(assignment)
        flipped_assignment[var] = 1
        flipped_solution = Solution(assignment=flipped_assignment, label="greedy-flip")
        feas = check_feasibility(problem.constraints, flipped_solution.assignment)
        if feas.status != "feasible":
            continue
        flipped_obj = evaluate_objective(problem, flipped_solution).total
        if flipped_obj < current_obj:
            assignment = flipped_assignment
    final_solution = Solution(assignment=assignment, label="greedy-final")
    final_obj = evaluate_objective(problem, final_solution).total
    return final_obj


def brute_force_solver(problem: Problem, max_states: int) -> Optional[float]:
    var_count = len(problem.variables)
    total_states = 2 ** var_count
    if total_states > max_states:
        return None
    best_obj: Optional[float] = None
    for bits in itertools.product([0, 1], repeat=var_count):
        assignment = dict(zip(problem.variables, bits))
        feas = check_feasibility(problem.constraints, assignment)
        if feas.status != "feasible":
            continue
        solution = Solution(assignment=assignment, label="brute")
        obj = evaluate_objective(problem, solution).total
        if best_obj is None or obj < best_obj:
            best_obj = obj
    return best_obj


def deterministic_anneal(problem: Problem, steps: int = 100) -> Optional[float]:
    # Placeholder deterministic annealing: use greedy result for determinism.
    set_seed(0)
    return greedy_solver(problem)
