from src.models import Problem, Solution
from src.objective import evaluate_objective


def test_objective_evaluation():
    problem = Problem(
        variables=["a", "b"],
        linear={"a": 1.0, "b": 2.0},
        quadratic={("a", "b"): -1.0},
        constraints=[],
    )
    solution = Solution(assignment={"a": 1, "b": 1}, label="test")
    obj = evaluate_objective(problem, solution)
    assert obj.linear_value == 3.0
    assert obj.quadratic_value == -1.0
    assert obj.total == 2.0
