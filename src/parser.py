from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from src.models import Constraint, Problem, Solution
from src.utils.determinism import TOL

VALID_CONSTRAINT_TYPES = {"linear_eq", "linear_ineq", "at_most_k", "xor"}


class ParseError(ValueError):
    pass


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON in {path}: {exc}") from exc


def _validate_variables(vars_list: List[str]) -> List[str]:
    if not isinstance(vars_list, list) or not vars_list:
        raise ParseError("variables must be a non-empty list")
    seen = set()
    for v in vars_list:
        if not isinstance(v, str):
            raise ParseError("variable ids must be strings")
        if v in seen:
            raise ParseError(f"duplicate variable id: {v}")
        seen.add(v)
    return vars_list


def _validate_linear(linear: dict, variables: List[str]) -> Dict[str, float]:
    if not isinstance(linear, dict):
        raise ParseError("linear must be an object")
    out: Dict[str, float] = {}
    for k, v in linear.items():
        if k not in variables:
            raise ParseError(f"linear term references unknown variable {k}")
        if not isinstance(v, (int, float)):
            raise ParseError(f"linear coefficient for {k} must be number")
        out[k] = float(v)
    return out


def _validate_quadratic(quadratic: list, variables: List[str]) -> Dict[Tuple[str, str], float]:
    if quadratic is None:
        return {}
    if not isinstance(quadratic, list):
        raise ParseError("quadratic must be an array of [i,j,coef]")
    out: Dict[Tuple[str, str], float] = {}
    for entry in quadratic:
        if not (isinstance(entry, list) or isinstance(entry, tuple)) or len(entry) != 3:
            raise ParseError("quadratic entries must be [i, j, coefficient]")
        i, j, coef = entry
        if i not in variables or j not in variables:
            raise ParseError(f"quadratic references unknown variables {i}, {j}")
        if not isinstance(coef, (int, float)):
            raise ParseError(f"quadratic coefficient for {i},{j} must be number")
        key = tuple(sorted((i, j)))
        if key in out:
            raise ParseError(f"duplicate quadratic entry for {key}")
        out[key] = float(coef)
    return out


def _validate_constraints(raw_constraints: list, variables: List[str]) -> List[Constraint]:
    if raw_constraints is None:
        return []
    if not isinstance(raw_constraints, list):
        raise ParseError("constraints must be an array")
    constraints: List[Constraint] = []
    for idx, c in enumerate(raw_constraints):
        if not isinstance(c, dict):
            raise ParseError(f"constraint at index {idx} must be object")
        ctype = c.get("type")
        if ctype not in VALID_CONSTRAINT_TYPES:
            raise ParseError(f"constraint at index {idx} has invalid type {ctype}")
        label = c.get("label") or f"c{idx}"
        lhs = c.get("lhs") or {}
        if not isinstance(lhs, dict):
            raise ParseError(f"constraint {label} lhs must be object")
        lhs_norm: Dict[str, float] = {}
        for k, v in lhs.items():
            if k not in variables:
                raise ParseError(f"constraint {label} references unknown variable {k}")
            if not isinstance(v, (int, float)):
                raise ParseError(f"constraint {label} coefficient for {k} must be number")
            lhs_norm[k] = float(v)
        rhs = c.get("rhs", 0.0)
        if not isinstance(rhs, (int, float)):
            raise ParseError(f"constraint {label} rhs must be number")
        constraints.append(Constraint(label=label, ctype=ctype, lhs=lhs_norm, rhs=float(rhs)))
    return constraints


def _validate_best_known(raw_best) -> Tuple[float, str] | None:
    if raw_best is None:
        return None
    if not isinstance(raw_best, dict):
        raise ParseError("best_known must be object")
    if "value" not in raw_best:
        raise ParseError("best_known missing value")
    value = raw_best["value"]
    if not isinstance(value, (int, float)):
        raise ParseError("best_known value must be number")
    label = raw_best.get("label", "best_known")
    if not isinstance(label, str):
        raise ParseError("best_known label must be string")
    return float(value), label


def load_problem(path: str) -> Problem:
    data = _load_json(Path(path))
    variables = _validate_variables(data.get("variables"))
    linear = _validate_linear(data.get("linear", {}), variables)
    quadratic = _validate_quadratic(data.get("quadratic", []), variables)
    constraints = _validate_constraints(data.get("constraints", []), variables)
    best_known = _validate_best_known(data.get("best_known"))
    metadata = data.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ParseError("metadata must be object")
    return Problem(
        variables=variables,
        linear=linear,
        quadratic=quadratic,
        constraints=constraints,
        best_known=best_known,
        metadata=metadata,
    )


def load_solution(path: str, problem: Problem) -> Solution:
    data = _load_json(Path(path))
    assignment_raw = data.get("assignment")
    if not isinstance(assignment_raw, dict):
        raise ParseError("solution assignment must be object")
    assignment: Dict[str, int] = {}
    for v in problem.variables:
        if v not in assignment_raw:
            raise ParseError(f"solution missing value for {v}")
        val = assignment_raw[v]
        if val not in (0, 1):
            raise ParseError(f"solution value for {v} must be 0 or 1")
        assignment[v] = int(val)
    extra_keys = set(assignment_raw.keys()) - set(problem.variables)
    if extra_keys:
        raise ParseError(f"solution has extra variables: {sorted(extra_keys)}")
    label = data.get("label") or "candidate"
    if not isinstance(label, str):
        raise ParseError("solution label must be string")
    metadata = data.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ParseError("solution metadata must be object")
    return Solution(assignment=assignment, label=label, metadata=metadata)
