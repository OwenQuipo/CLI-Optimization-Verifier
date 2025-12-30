from __future__ import annotations

from typing import Dict, List, Optional

from src.models import (
    FeasibilityResult,
    ObjectiveResult,
    Problem,
    RunResult,
    SensitivityEntry,
    Solution,
)


def _fmt_float(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") if value is not None else "n/a"


def _render_feasibility(feas: FeasibilityResult) -> List[str]:
    lines = [f"Feasibility: {feas.status}"]
    if feas.violations:
        lines.append("Violations:")
        for v in feas.violations:
            lines.append(f"  {v.label}: {_fmt_float(v.amount)}")
    else:
        lines.append("Violations: none")
    if feas.binding:
        lines.append("Binding constraints:")
        for label in feas.binding:
            lines.append(f"  {label}")
    return lines


def _render_objective(obj: Optional[ObjectiveResult]) -> List[str]:
    if obj is None:
        return ["Objective: n/a"]
    return [
        "Objective:",
        f"  linear={_fmt_float(obj.linear_value)}",
        f"  quadratic={_fmt_float(obj.quadratic_value)}",
        f"  total={_fmt_float(obj.total)}",
    ]


def _render_comparator(best_known: Optional[tuple], gap: Optional[float]) -> List[str]:
    lines: List[str] = ["Comparator:"]
    if best_known is None:
        lines.append("  best_known: none")
        lines.append("  gap: unknown")
        return lines
    best_val, label = best_known
    lines.append(f"  best_known: {_fmt_float(best_val)} (label={label})")
    if gap is None:
        lines.append("  gap: undefined (best_known is zero or missing)")
    else:
        lines.append(f"  gap: {_fmt_float(gap)}%")
    return lines


def _render_sensitivity(entries: List[SensitivityEntry]) -> List[str]:
    lines: List[str] = ["Sensitivity (bit flips):"]
    if not entries:
        lines.append("  none (skipped)")
        return lines
    for e in entries:
        feas = "feasible" if e.feasible_after_flip else "infeasible"
        lines.append(f"  {e.var} flip -> {_fmt_float(e.delta)} ({feas})")
    return lines


def _render_solvers(comparison: Dict[str, Optional[float]]) -> List[str]:
    lines: List[str] = ["Solver comparison:"]
    if not comparison:
        lines.append("  none")
        return lines
    for name in sorted(comparison.keys()):
        val = comparison[name]
        if val is None:
            lines.append(f"  {name}: skipped")
        else:
            lines.append(f"  {name}: {_fmt_float(val)}")
    return lines


def _render_version(meta: Optional[dict[str, str]]) -> List[str]:
    if not meta:
        return []
    lines: List[str] = ["Version:"]
    for key in sorted(meta.keys()):
        lines.append(f"  {key}={meta[key]}")
    return lines


def render_report(
    problem: Problem, solution: Solution, result: RunResult, version_meta: Optional[dict[str, str]] = None
) -> str:
    lines: List[str] = [
        f"Input: vars={len(problem.variables)}, constraints={len(problem.constraints)}, candidate={solution.label}"
    ]
    lines.extend(_render_feasibility(result.feasibility))
    lines.extend(_render_objective(result.objective))
    lines.extend(_render_comparator(result.best_known, result.gap))
    lines.extend(_render_sensitivity(result.sensitivity))
    lines.extend(_render_solvers(result.solver_comparison))
    lines.extend(_render_version(version_meta))
    return "\n".join(lines)
