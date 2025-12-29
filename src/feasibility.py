from __future__ import annotations

from typing import Dict, List

from src.models import Constraint, FeasibilityResult, Violation
from src.utils.determinism import TOL


def _evaluate_linear(lhs: Dict[str, float], assignment: Dict[str, int]) -> float:
    return sum(coeff * assignment.get(var, 0) for var, coeff in lhs.items())


def evaluate_constraint(constraint: Constraint, assignment: Dict[str, int]) -> tuple[bool, float, bool]:
    """Return (satisfied, violation_amount, binding)."""
    lhs_value = _evaluate_linear(constraint.lhs, assignment)
    rhs = constraint.rhs
    binding = False
    if constraint.ctype == "linear_eq":
        diff = abs(lhs_value - rhs)
        satisfied = diff <= TOL
        binding = satisfied
        violation = 0.0 if satisfied else diff
    elif constraint.ctype == "linear_ineq":
        diff = lhs_value - rhs
        satisfied = diff <= TOL
        binding = abs(diff) <= TOL
        violation = 0.0 if satisfied else diff
    elif constraint.ctype == "at_most_k":
        diff = lhs_value - rhs
        satisfied = diff <= TOL
        binding = abs(diff) <= TOL
        violation = 0.0 if satisfied else diff
    elif constraint.ctype == "xor":
        diff = lhs_value - 1.0
        satisfied = abs(diff) <= TOL
        binding = satisfied
        violation = 0.0 if satisfied else abs(diff)
    else:
        return False, float("inf"), False
    return satisfied, violation, binding


def check_feasibility(constraints: List[Constraint], assignment: Dict[str, int]) -> FeasibilityResult:
    violations: List[Violation] = []
    binding: List[str] = []
    for c in constraints:
        sat, viol, bind = evaluate_constraint(c, assignment)
        if not sat:
            violations.append(Violation(label=c.label, amount=viol))
        elif bind:
            binding.append(c.label)
    status = "feasible" if not violations else "infeasible"
    return FeasibilityResult(status=status, violations=violations, binding=binding)
