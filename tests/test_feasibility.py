from src.feasibility import check_feasibility
from src.models import Constraint


def test_feasible_and_binding():
    constraints = [
        Constraint(label="cap", ctype="linear_ineq", lhs={"a": 1}, rhs=1),
        Constraint(label="xor1", ctype="xor", lhs={"a": 1}, rhs=0),
    ]
    result = check_feasibility(constraints, {"a": 1})
    assert result.status == "feasible"
    assert not result.violations
    assert "cap" in result.binding or "xor1" in result.binding


def test_infeasible_violation_report():
    constraints = [
        Constraint(label="cap", ctype="linear_ineq", lhs={"a": 2}, rhs=1)
    ]
    result = check_feasibility(constraints, {"a": 1})
    assert result.status == "infeasible"
    assert result.violations[0].label == "cap"
