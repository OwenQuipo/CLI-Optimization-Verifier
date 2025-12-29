from __future__ import annotations

from typing import Optional, Tuple

from src.models import Problem
from src.utils.determinism import TOL


def compute_gap(candidate_value: float, best_known: Optional[Tuple[float, str]]) -> Optional[float]:
    if best_known is None:
        return None
    best_val, _ = best_known
    if abs(best_val) <= TOL:
        return None
    return (candidate_value - best_val) / abs(best_val) * 100.0


def get_best_known(problem: Problem) -> Optional[Tuple[float, str]]:
    return problem.best_known
