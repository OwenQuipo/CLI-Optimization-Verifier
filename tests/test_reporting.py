from src.models import (
    FeasibilityResult,
    ObjectiveResult,
    Problem,
    RunResult,
    SensitivityEntry,
    Solution,
    Violation,
)
from src.reporting import render_report


def test_render_report_deterministic_snapshot():
    problem = Problem(
        variables=["x1", "x2"],
        linear={"x1": 1.0, "x2": 1.0},
        quadratic={},
        constraints=[],
        best_known=(1.0, "bk"),
    )
    solution = Solution(assignment={"x1": 1, "x2": 0}, label="cand")
    feas = FeasibilityResult(status="feasible", violations=[], binding=[])
    obj = ObjectiveResult(linear_value=1.0, quadratic_value=0.0, total=1.0)
    sensitivity = [SensitivityEntry(var="x1", delta=0.0, feasible_after_flip=True)]
    run = RunResult(
        feasibility=feas,
        objective=obj,
        gap=0.0,
        best_known=problem.best_known,
        sensitivity=sensitivity,
        solver_comparison={},
    )
    report = render_report(problem, solution, run)
    expected = (
        "Input: vars=2, constraints=0, candidate=cand\n"
        "Feasibility: feasible\n"
        "Violations: none\n"
        "Objective:\n"
        "  linear=1\n"
        "  quadratic=0\n"
        "  total=1\n"
        "Comparator:\n"
        "  best_known: 1 (label=bk)\n"
        "  gap: 0%\n"
        "Sensitivity (bit flips):\n"
        "  x1 flip -> 0 (feasible)\n"
        "Solver comparison:\n"
        "  none"
    )
    assert report == expected
