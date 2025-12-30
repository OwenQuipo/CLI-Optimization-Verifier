from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import re
from typing import Any, Dict, List, Tuple

Draft = Dict[str, Any]

QUAD_PATTERN = re.compile(
    r"([+-]?\s*\d*\.?\d*)\s*([A-Za-z][A-Za-z0-9_]*)\s*[*x]\s*([A-Za-z][A-Za-z0-9_]*)"
)


@dataclasses.dataclass
class WarningEntry:
    code: str
    message: str
    severity: str  # info | warn | error
    field_path: str | None = None
    assumption: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.field_path:
            payload["field_path"] = self.field_path
        if self.assumption:
            payload["assumption"] = self.assumption
        return payload


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _empty_draft(text: str) -> Draft:
    return {
        "variables": [],
        "objective": {"sense": "min", "linear_terms": [], "quadratic_terms": []},
        "constraints": [],
        "candidate_solution": [],
        "metadata": {
            "source_text_hash": _hash_text(text),
            "draft_version": "v0.2",
            "created_at": _now_iso(),
        },
    }


def _parse_linear_expr(expr: str) -> Tuple[List[Tuple[str, float]], List[WarningEntry]]:
    """
    Parse a simple linear expression like "3 x1 - x2 + 2x3".
    Returns list of (var, coeff).
    """
    warnings: List[WarningEntry] = []
    tokens = re.finditer(r"([+-]?\s*\d*\.?\d*)\s*([A-Za-z][A-Za-z0-9_]*)", expr)
    terms: List[Tuple[str, float]] = []
    for match in tokens:
        raw_coeff = match.group(1).replace(" ", "")
        var = match.group(2)
        if raw_coeff in ("", "+", "-"):
            coeff = -1.0 if raw_coeff.strip() == "-" else 1.0
            warnings.append(
                WarningEntry(
                    code="assumed_unit_coeff",
                    message=f"Assumed coefficient 1 for term with variable {var}",
                    severity="warn",
                    field_path=f"objective.linear_terms[{var}]",
                    assumption="No explicit coefficient found; defaulted to 1",
                )
            )
        else:
            try:
                coeff = float(raw_coeff)
            except ValueError:
                warnings.append(
                    WarningEntry(
                        code="invalid_coeff",
                        message=f"Could not parse coefficient '{raw_coeff}' for variable {var}",
                        severity="error",
                        field_path=f"objective.linear_terms[{var}]",
                    )
                )
                continue
        terms.append((var, coeff))
    return terms, warnings


def _parse_quadratic(expr: str) -> Tuple[List[Tuple[str, str, float]], List[WarningEntry]]:
    warnings: List[WarningEntry] = []
    triples: List[Tuple[str, str, float]] = []
    tokens = QUAD_PATTERN.finditer(expr)
    for match in tokens:
        raw_coeff = match.group(1).replace(" ", "")
        var_i = match.group(2)
        var_j = match.group(3)
        if raw_coeff in ("", "+", "-"):
            coeff = -1.0 if raw_coeff.strip() == "-" else 1.0
            warnings.append(
                WarningEntry(
                    code="assumed_unit_coeff",
                    message=f"Assumed coefficient 1 for quadratic term {var_i}*{var_j}",
                    severity="warn",
                    field_path=f"objective.quadratic_terms[{var_i},{var_j}]",
                    assumption="No explicit coefficient found; defaulted to 1",
                )
            )
        else:
            try:
                coeff = float(raw_coeff)
            except ValueError:
                warnings.append(
                    WarningEntry(
                        code="invalid_coeff",
                        message=f"Could not parse coefficient '{raw_coeff}' for quadratic term {var_i}*{var_j}",
                        severity="error",
                        field_path=f"objective.quadratic_terms[{var_i},{var_j}]",
                    )
                )
                continue
        triples.append((var_i, var_j, coeff))
    return triples, warnings


def _parse_constraint_line(line: str) -> Tuple[dict[str, Any] | None, List[WarningEntry]]:
    warnings: List[WarningEntry] = []
    m = re.match(
        r"(?:(?P<label>[A-Za-z0-9_\-]+)\s*:\s*)?(?P<body>.+?)\s*(?P<sense><=|>=|==)\s*(?P<rhs>[-+]?\d*\.?\d+)",
        line,
    )
    if not m:
        return None, warnings
    label = m.group("label") or ""
    body = m.group("body")
    sense = m.group("sense")
    rhs = float(m.group("rhs"))
    terms, term_warnings = _parse_linear_expr(body)
    warnings.extend(term_warnings)
    constraint = {
        "label": label,
        "sense": sense,
        "terms": [{"var": var, "coeff": coeff} for var, coeff in terms],
        "rhs": rhs,
    }
    return constraint, warnings


def translate_text_to_draft(text: str) -> dict[str, Any]:
    """
    Rule-based extractor for a structured draft.
    Returns translation_result with warnings and needs_clarification flag.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    warnings: List[WarningEntry] = []
    clarification_questions: List[str] = []
    draft = _empty_draft(text)

    # Variables
    vars_found: List[str] = []
    for line in lines:
        m = re.match(r"(?i)^(variables|vars)\s*[:\-]\s*(.+)$", line)
        if m:
            raw = m.group(2)
            tokens = [tok.strip() for tok in re.split(r"[\s,]+", raw) if tok.strip()]
            vars_found.extend(tokens)
    if not vars_found:
        # Fall back to variables seen in objective/constraints/solution
        candidate_vars = set(re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\b", text))
        vars_found = sorted(v for v in candidate_vars if not v.lower() in {"minimize", "maximize", "subject", "st"})
    draft["variables"] = [{"id": v} for v in vars_found]
    if not vars_found:
        warnings.append(
            WarningEntry(
                code="missing_variables",
                message="Could not find any variable definitions.",
                severity="error",
                field_path="variables",
            )
        )
        clarification_questions.append("List the binary decision variables (e.g., x1, x2).")

    # Objective
    objective_lines = [ln for ln in lines if re.search(r"(?i)(minimize|maximize|objective)", ln)]
    if objective_lines:
        line = objective_lines[0]
        sense = "min" if re.search(r"(?i)min", line) else "max" if re.search(r"(?i)max", line) else "min"
        draft["objective"]["sense"] = sense
        objective_body = re.sub(r"(?i)objective\s*[:\-]*", "", line)
        objective_body = re.sub(r"(?i)(minimize|maximize|min|max)\s*", "", objective_body, count=1)
        quad_terms, quad_warnings = _parse_quadratic(objective_body)
        objective_body_linear = QUAD_PATTERN.sub(" ", objective_body)
        terms, term_warnings = _parse_linear_expr(objective_body_linear)
        warnings.extend(term_warnings)
        draft["objective"]["linear_terms"] = [{"var": var, "coeff": coeff} for var, coeff in terms]
        warnings.extend(quad_warnings)
        draft["objective"]["quadratic_terms"] = [
            {"var_i": i, "var_j": j, "coeff": coeff} for i, j, coeff in quad_terms
        ]
        if not terms and not quad_terms:
            warnings.append(
                WarningEntry(
                    code="missing_objective_terms",
                    message="Objective found but no terms parsed.",
                    severity="error",
                    field_path="objective",
                )
            )
            clarification_questions.append("Provide objective terms like 'minimize 3 x1 + 2 x2'.")
    else:
        warnings.append(
            WarningEntry(
                code="missing_objective",
                message="Could not locate an objective (minimize/maximize).",
                severity="error",
                field_path="objective",
            )
        )
        clarification_questions.append("Specify an objective, e.g., 'Minimize 2 x1 + 3 x2'.")

    # Constraints
    constraints: List[dict[str, Any]] = []
    for line in lines:
        if "<=" in line or ">=" in line or "==" in line:
            constraint, cw = _parse_constraint_line(line)
            warnings.extend(cw)
            if constraint:
                constraints.append(constraint)
    draft["constraints"] = constraints
    if not constraints:
        warnings.append(
            WarningEntry(
                code="missing_constraints",
                message="No constraints with <=, >=, or == were parsed.",
                severity="error",
                field_path="constraints",
            )
        )
        clarification_questions.append("Provide at least one constraint using <=, ==, or >=.")

    # Candidate solution
    solution_lines = [ln for ln in lines if re.search(r"(?i)(solution|assignment)", ln)]
    assignments: List[dict[str, Any]] = []
    for line in solution_lines:
        pairs = re.finditer(r"([A-Za-z][A-Za-z0-9_]*)\s*=?\s*([01])", line)
        for pair in pairs:
            assignments.append({"var": pair.group(1), "value": int(pair.group(2))})
    draft["candidate_solution"] = assignments
    if not assignments:
        warnings.append(
            WarningEntry(
                code="missing_candidate_solution",
                message="No candidate solution assignments were extracted.",
                severity="error",
                field_path="candidate_solution",
            )
        )
        clarification_questions.append("Provide a candidate solution like 'solution: x1=1, x2=0'.")

    needs_clarification = any(w.severity == "error" for w in warnings)
    result = {
        "structured_draft": draft,
        "warnings": [w.to_dict() for w in warnings],
        "needs_clarification": needs_clarification,
    }
    if needs_clarification:
        result["clarification_questions"] = clarification_questions
    return result


def _warn(code: str, message: str, field: str | None = None, assumption: str | None = None, severity: str = "warn"):
    return WarningEntry(code=code, message=message, severity=severity, field_path=field, assumption=assumption)


def _validated_number(value: Any, field_path: str, warnings: List[WarningEntry]) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    warnings.append(_warn("invalid_number", f"Expected number at {field_path}", field_path, severity="error"))
    return None


def validate_structured_draft(draft: Draft) -> Tuple[Draft, List[WarningEntry]]:
    """
    Validate and normalize the structured draft in-place and return it plus warnings.
    Adds errors to warnings for blocking conditions.
    """
    warnings: List[WarningEntry] = []

    # Variables
    variables = draft.get("variables") or []
    seen: set[str] = set()
    clean_vars: List[dict[str, Any]] = []
    for idx, item in enumerate(variables):
        vid = (item or {}).get("id")
        if not isinstance(vid, str) or not vid:
            warnings.append(_warn("invalid_var", "Variable id must be a non-empty string", f"variables[{idx}]", severity="error"))
            continue
        if vid in seen:
            warnings.append(_warn("duplicate_var", f"Duplicate variable id {vid}", f"variables[{idx}]", severity="error"))
            continue
        seen.add(vid)
        label = item.get("label") if isinstance(item, dict) else None
        if label is not None and not isinstance(label, str):
            warnings.append(_warn("invalid_label", f"Label for {vid} must be string", f"variables[{idx}].label", severity="warn"))
            label = None
        clean_vars.append({"id": vid, "label": label})
    if not clean_vars:
        warnings.append(_warn("no_variables", "No valid variables provided", "variables", severity="error"))
    draft["variables"] = clean_vars

    # Objective
    objective = draft.get("objective") or {}
    sense = objective.get("sense", "min")
    if sense not in ("min", "max"):
        warnings.append(_warn("invalid_objective_sense", "Objective sense must be 'min' or 'max'", "objective.sense", severity="error"))
        sense = "min"
    draft.setdefault("objective", {})
    draft["objective"]["sense"] = sense
    linear_terms = objective.get("linear_terms") or []
    clean_linear: List[dict[str, Any]] = []
    for idx, term in enumerate(linear_terms):
        var = (term or {}).get("var")
        coeff = _validated_number((term or {}).get("coeff"), f"objective.linear_terms[{idx}].coeff", warnings)
        if not isinstance(var, str):
            warnings.append(_warn("invalid_var_ref", "Objective term variable must be a string", f"objective.linear_terms[{idx}].var", severity="error"))
            continue
        if coeff is None:
            continue
        clean_linear.append({"var": var, "coeff": coeff})
    draft["objective"]["linear_terms"] = clean_linear
    quad_terms = objective.get("quadratic_terms") or []
    clean_quad: List[dict[str, Any]] = []
    for idx, term in enumerate(quad_terms):
        var_i = (term or {}).get("var_i")
        var_j = (term or {}).get("var_j")
        coeff = _validated_number((term or {}).get("coeff"), f"objective.quadratic_terms[{idx}].coeff", warnings)
        if not isinstance(var_i, str) or not isinstance(var_j, str):
            warnings.append(_warn("invalid_var_ref", "Quadratic term variables must be strings", f"objective.quadratic_terms[{idx}]", severity="error"))
            continue
        if coeff is None:
            continue
        clean_quad.append({"var_i": var_i, "var_j": var_j, "coeff": coeff})
    draft["objective"]["quadratic_terms"] = clean_quad
    if not clean_linear and not clean_quad:
        warnings.append(_warn("empty_objective", "Objective has no terms", "objective", severity="error"))

    # Constraints
    constraints = draft.get("constraints") or []
    clean_constraints: List[dict[str, Any]] = []
    for idx, c in enumerate(constraints):
        sense = (c or {}).get("sense")
        if sense not in ("<=", "==", ">="):
            warnings.append(_warn("invalid_constraint_sense", "Constraint sense must be <=, ==, or >=", f"constraints[{idx}].sense", severity="error"))
            continue
        rhs = _validated_number((c or {}).get("rhs"), f"constraints[{idx}].rhs", warnings)
        if rhs is None:
            continue
        label = (c or {}).get("label") or f"c{idx}"
        terms = (c or {}).get("terms") or []
        clean_terms: List[dict[str, Any]] = []
        for jdx, term in enumerate(terms):
            var = (term or {}).get("var")
            coeff = _validated_number((term or {}).get("coeff"), f"constraints[{idx}].terms[{jdx}].coeff", warnings)
            if not isinstance(var, str):
                warnings.append(_warn("invalid_var_ref", "Constraint term variable must be string", f"constraints[{idx}].terms[{jdx}]", severity="error"))
                continue
            if coeff is None:
                continue
            clean_terms.append({"var": var, "coeff": coeff})
        if not clean_terms:
            warnings.append(_warn("empty_constraint", f"Constraint {label} has no terms", f"constraints[{idx}]", severity="error"))
            continue
        clean_constraints.append({"label": label, "sense": sense, "terms": clean_terms, "rhs": rhs})
    if not clean_constraints:
        warnings.append(_warn("no_constraints", "No valid constraints provided", "constraints", severity="error"))
    draft["constraints"] = clean_constraints

    # Candidate solution
    cand = draft.get("candidate_solution") or []
    clean_assignments: List[dict[str, Any]] = []
    for idx, entry in enumerate(cand):
        var = (entry or {}).get("var")
        val = (entry or {}).get("value")
        if not isinstance(var, str):
            warnings.append(_warn("invalid_var_ref", "Candidate solution var must be string", f"candidate_solution[{idx}]", severity="error"))
            continue
        if val not in (0, 1):
            warnings.append(_warn("invalid_candidate_value", "Candidate solution values must be 0 or 1", f"candidate_solution[{idx}]", severity="error"))
            continue
        clean_assignments.append({"var": var, "value": int(val)})
    if not clean_assignments:
        warnings.append(_warn("no_candidate_solution", "No valid candidate solution provided", "candidate_solution", severity="error"))
    draft["candidate_solution"] = clean_assignments

    draft.setdefault("metadata", {})
    return draft, warnings


def draft_to_internal_json(draft: Draft) -> Tuple[str, str, List[WarningEntry]]:
    """
    Convert validated draft to problem.json and solution.json strings.
    Returns warnings (including informational transformations).
    """
    draft, validation_warnings = validate_structured_draft(draft)
    has_errors = any(w.severity == "error" for w in validation_warnings)
    if has_errors:
        return "", "", validation_warnings

    variables = [v["id"] for v in draft["variables"]]
    variable_set = set(variables)
    conversion_warnings: List[WarningEntry] = []

    # Objective conversion; treat maximization by negating coefficients.
    objective_sense = draft["objective"]["sense"]
    linear = {}
    for term in draft["objective"]["linear_terms"]:
        if term["var"] not in variable_set:
            conversion_warnings.append(_warn("unknown_objective_var", f"Objective references unknown variable {term['var']}", "objective", severity="error"))
            continue
        linear[term["var"]] = float(term["coeff"]) * (-1 if objective_sense == "max" else 1)
    quadratic_list = []
    for term in draft["objective"]["quadratic_terms"]:
        if term["var_i"] not in variable_set or term["var_j"] not in variable_set:
            conversion_warnings.append(_warn("unknown_objective_var", f"Quadratic term references unknown variables {term['var_i']}, {term['var_j']}", "objective", severity="error"))
            continue
        quadratic_list.append([term["var_i"], term["var_j"], float(term["coeff"]) * (-1 if objective_sense == "max" else 1)])
    if objective_sense == "max":
        conversion_warnings.append(
            _warn(
                "objective_negated",
                "Max objective coefficients negated for verifier (verifier assumes minimization).",
                "objective.sense",
                assumption="Verifier expects minimization; transformed internally.",
                severity="info",
            )
        )

    constraints_json = []
    for constraint in draft["constraints"]:
        lhs = {}
        for term in constraint["terms"]:
            if term["var"] not in variable_set:
                conversion_warnings.append(
                    _warn("unknown_constraint_var", f"Constraint references unknown variable {term['var']}", f"constraints[{constraint['label']}]", severity="error")
                )
                continue
            lhs[term["var"]] = float(term["coeff"])
        rhs = float(constraint["rhs"])
        constraint_sense = constraint["sense"]
        ctype = "linear_eq" if constraint_sense == "==" else "linear_ineq"
        if constraint_sense == ">=":
            lhs = {k: -v for k, v in lhs.items()}
            rhs = -rhs
            conversion_warnings.append(
                _warn(
                    "normalized_ge_constraint",
                    f"Constraint {constraint['label']} with >= converted to <= form for verifier.",
                    f"constraints[{constraint['label']}]",
                    assumption="Verifier expects <= inequalities.",
                    severity="info",
                )
            )
        constraints_json.append(
            {
                "label": constraint["label"],
                "type": ctype,
                "lhs": lhs,
                "rhs": rhs,
            }
        )

    candidate_map = {}
    for entry in draft["candidate_solution"]:
        if entry["var"] not in variable_set:
            conversion_warnings.append(
                _warn("unknown_candidate_var", f"Candidate solution references unknown variable {entry['var']}", "candidate_solution", severity="error")
            )
            continue
        candidate_map[entry["var"]] = int(entry["value"])
    missing_assignments = [v for v in variables if v not in candidate_map]
    if missing_assignments:
        conversion_warnings.append(
            _warn(
                "missing_candidate_values",
                f"Candidate solution missing assignments for {missing_assignments}",
                "candidate_solution",
                severity="error",
            )
        )
    assignment = {var: candidate_map[var] for var in variables if var in candidate_map}

    warnings = validation_warnings + conversion_warnings
    if any(w.severity == "error" for w in warnings):
        return "", "", warnings

    metadata = draft.get("metadata", {}) or {}
    metadata = dict(metadata)
    metadata.setdefault("objective_sense", objective_sense)

    problem_json = {
        "variables": variables,
        "linear": linear,
        "quadratic": quadratic_list,
        "constraints": constraints_json,
        "metadata": metadata,
    }
    solution_json = {
        "label": "approved_candidate",
        "assignment": assignment,
        "metadata": {"source": "ui"},
    }

    return json.dumps(problem_json), json.dumps(solution_json), warnings
