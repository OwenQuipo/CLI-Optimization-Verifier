import pytest

from src.parser import ParseError, load_problem, load_solution


def test_load_problem_and_solution(tmp_path):
    problem_path = tmp_path / "problem.json"
    solution_path = tmp_path / "solution.json"
    problem_path.write_text(
        """
{
  "variables": ["a", "b"],
  "linear": {"a": 1, "b": 2},
  "quadratic": [["a","b", -1]],
  "constraints": [
    {"type": "linear_ineq", "label": "cap", "lhs": {"a": 1, "b": 1}, "rhs": 1}
  ]
}
""",
        encoding="utf-8",
    )
    solution_path.write_text(
        """
{
  "label": "cand",
  "assignment": {"a": 1, "b": 0}
}
""",
        encoding="utf-8",
    )
    problem = load_problem(str(problem_path))
    solution = load_solution(str(solution_path), problem)
    assert problem.variables == ["a", "b"]
    assert problem.linear["a"] == 1
    assert ("a", "b") in problem.quadratic
    assert solution.assignment == {"a": 1, "b": 0}


def test_solution_missing_variable_raises(tmp_path):
    problem_path = tmp_path / "problem.json"
    solution_path = tmp_path / "solution.json"
    problem_path.write_text(
        '{"variables":["a"], "linear":{"a":1}}',
        encoding="utf-8",
    )
    solution_path.write_text(
        '{"assignment":{}}',
        encoding="utf-8",
    )
    problem = load_problem(str(problem_path))
    with pytest.raises(ParseError):
        load_solution(str(solution_path), problem)
