from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Constraint:
    """Represents a single constraint with explicit type."""

    label: str
    ctype: str  # linear_eq, linear_ineq, at_most_k, xor
    lhs: Dict[str, float] = field(default_factory=dict)
    rhs: float = 0.0


@dataclass(frozen=True)
class Problem:
    variables: List[str]
    linear: Dict[str, float]
    quadratic: Dict[Tuple[str, str], float]  # normalized with i<=j
    constraints: List[Constraint]
    best_known: Optional[Tuple[float, str]] = None  # (value, label)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Solution:
    assignment: Dict[str, int]
    label: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ObjectiveResult:
    linear_value: float
    quadratic_value: float
    total: float


@dataclass(frozen=True)
class Violation:
    label: str
    amount: float


@dataclass(frozen=True)
class FeasibilityResult:
    status: str  # feasible, infeasible, unknown
    violations: List[Violation] = field(default_factory=list)
    binding: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SensitivityEntry:
    var: str
    delta: float
    feasible_after_flip: bool


@dataclass(frozen=True)
class RunResult:
    feasibility: FeasibilityResult
    objective: Optional[ObjectiveResult]
    gap: Optional[float]
    best_known: Optional[Tuple[float, str]]
    sensitivity: List[SensitivityEntry]
    solver_comparison: Dict[str, Optional[float]]
