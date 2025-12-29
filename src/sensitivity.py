from __future__ import annotations

from typing import List

from src.feasibility import check_feasibility
from src.models import Problem, SensitivityEntry, Solution
from src.objective import evaluate_objective


def sensitivity_analysis(problem: Problem, base_solution: Solution, base_obj: float) -> List[SensitivityEntry]:
    results: List[SensitivityEntry] = []
    for var in problem.variables:
        flipped_assignment = dict(base_solution.assignment)
        flipped_assignment[var] = 1 - flipped_assignment[var]
        flipped_solution = Solution(assignment=flipped_assignment, label=f"{base_solution.label}-flip-{var}")
        feas = check_feasibility(problem.constraints, flipped_solution.assignment)
        obj = evaluate_objective(problem, flipped_solution)
        delta = obj.total - base_obj
        results.append(
            SensitivityEntry(
                var=var,
                delta=delta,
                feasible_after_flip=(feas.status == "feasible"),
            )
        )
    results.sort(key=lambda e: (abs(e.delta), e.var))
    return results
