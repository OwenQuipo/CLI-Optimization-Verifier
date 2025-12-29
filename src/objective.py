from __future__ import annotations

from src.models import ObjectiveResult, Problem, Solution


def evaluate_objective(problem: Problem, solution: Solution) -> ObjectiveResult:
    assignment = solution.assignment
    linear_value = sum(problem.linear.get(v, 0.0) * assignment.get(v, 0) for v in problem.variables)
    quadratic_value = 0.0
    for (i, j), coef in problem.quadratic.items():
        quadratic_value += coef * assignment.get(i, 0) * assignment.get(j, 0)
    total = linear_value + quadratic_value
    return ObjectiveResult(linear_value=linear_value, quadratic_value=quadratic_value, total=total)
