const problemInput = document.getElementById("problem-input");
const solutionInput = document.getElementById("solution-input");
const loadExampleBtn = document.getElementById("load-example");
const verifyBtn = document.getElementById("verify-btn");
const statusEl = document.getElementById("status");
const exitCodeEl = document.getElementById("exit-code");
const exitStatusEl = document.getElementById("exit-status");
const stdoutEl = document.getElementById("stdout");
const stderrEl = document.getElementById("stderr");
const stderrSection = document.getElementById("stderr-section");
const validationSection = document.getElementById("validation-section");
const validationEl = document.getElementById("validation-warnings");
const cliVersionEl = document.getElementById("cli-version");
const uiVersionEl = document.getElementById("ui-version");
const problemFileInput = document.getElementById("problem-file");
const solutionFileInput = document.getElementById("solution-file");

const tabs = Array.from(document.querySelectorAll(".tab"));
const tabContents = Array.from(document.querySelectorAll(".tab-content"));

const draftTextInput = document.getElementById("draft-text-input");
const draftGenerateBtn = document.getElementById("draft-generate-btn");
const draftStatus = document.getElementById("draft-status");
const draftBanner = document.getElementById("draft-banner");
const bannerSubcopy = document.getElementById("banner-subcopy");
const warningsPanel = document.getElementById("warnings-panel");
const warningsListEl = document.getElementById("warnings-list");
const clarificationPanel = document.getElementById("clarification-panel");
const clarificationList = document.getElementById("clarification-questions");
const draftEditor = document.getElementById("draft-editor");
const draftSections = document.getElementById("draft-sections");
const approvalActions = document.getElementById("approval-actions");
const approveVerifyBtn = document.getElementById("approve-verify-btn");
const rerunDraftBtn = document.getElementById("rerun-draft-btn");
const approvalStatus = document.getElementById("approval-status");
const downloadJsonBtn = document.getElementById("download-json-btn");
const compareSolversToggle = document.getElementById("compare-solvers-toggle");
const draftResults = document.getElementById("draft-results");
const draftExitCodeEl = document.getElementById("draft-exit-code");
const draftExitStatusEl = document.getElementById("draft-exit-status");
const draftStdoutEl = document.getElementById("draft-stdout");
const draftStderrEl = document.getElementById("draft-stderr");
const draftStderrSection = document.getElementById("draft-stderr-section");

const EXIT_STATUS = {
  0: "Feasible",
  1: "Infeasible",
  2: "Error",
};

const state = {
  tab: "json",
  translationWarnings: [],
  validationWarnings: [],
  draft: null,
  needsClarification: false,
  clarificationQuestions: [],
  draftLoading: false,
  approvalInFlight: false,
  lastInternalProblem: "",
  lastInternalSolution: "",
};

const setStatus = (el, text, mode = "idle") => {
  el.textContent = text;
  el.classList.remove("ok", "error", "pending");
  if (mode === "ok") el.classList.add("ok");
  if (mode === "error") el.classList.add("error");
  if (mode === "pending") el.classList.add("pending");
};

const switchTab = (tabName) => {
  state.tab = tabName;
  tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));
  tabContents.forEach((c) => c.classList.toggle("active", c.dataset.content === tabName));
};

const readFileInto = (fileInput, targetInput) => {
  const [file] = fileInput.files;
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    targetInput.value = e.target?.result || "";
  };
  reader.readAsText(file);
};

const loadExamples = async () => {
  setStatus(statusEl, "Loading examples...", "pending");
  try {
    const [problemResp, solutionResp] = await Promise.all([
      fetch("/examples/problem.json"),
      fetch("/examples/solution.json"),
    ]);
    if (!problemResp.ok || !solutionResp.ok) {
      throw new Error("Failed to load examples");
    }
    problemInput.value = await problemResp.text();
    solutionInput.value = await solutionResp.text();
    setStatus(statusEl, "Examples loaded", "ok");
  } catch (err) {
    setStatus(statusEl, String(err), "error");
  }
};

const renderResult = (data, target = "json") => {
  const exitCode = typeof data.exitCode === "number" ? data.exitCode : -1;
  const label = EXIT_STATUS[exitCode] || "Error";
  if (target === "draft") {
    draftExitCodeEl.textContent = exitCode;
    draftExitStatusEl.textContent = label;
    draftStdoutEl.textContent = data.stdout ?? "";
    draftStderrEl.textContent = data.stderr ?? "";
    if (data.stderr) {
      draftStderrSection.open = exitCode === 2;
      draftStderrSection.style.display = "";
    } else {
      draftStderrSection.style.display = "none";
    }
    draftResults.style.display = "block";
  }
  exitCodeEl.textContent = exitCode;
  exitStatusEl.textContent = label;
  stdoutEl.textContent = data.stdout ?? "";
  stderrEl.textContent = data.stderr ?? "";
  if (data.stderr) {
    stderrSection.open = exitCode === 2;
    stderrSection.style.display = "";
  } else {
    stderrSection.open = false;
    stderrSection.style.display = "none";
  }
  const warnings = Array.isArray(data.validationWarnings) ? data.validationWarnings : [];
  if (warnings.length > 0) {
    validationEl.textContent = warnings.join("\n");
    validationSection.style.display = "";
    validationSection.open = exitCode === 2;
  } else {
    validationEl.textContent = "";
    validationSection.style.display = "none";
    validationSection.open = false;
  }
  const version = data.version || {};
  cliVersionEl.textContent = version.cli_version || "unknown";
  uiVersionEl.textContent = version.ui_version || "ui-local";

  if (exitCode === 0) {
    setStatus(statusEl, "Feasible (exit code 0)", "ok");
    if (target === "draft") setStatus(approvalStatus, "Verified feasible", "ok");
  } else if (exitCode === 1) {
    setStatus(statusEl, "Infeasible (exit code 1)", "error");
    if (target === "draft") setStatus(approvalStatus, "Verified infeasible", "error");
  } else {
    setStatus(statusEl, `Error (exit code ${exitCode})`, "error");
    if (target === "draft") setStatus(approvalStatus, `Error (exit code ${exitCode})`, "error");
  }
};

const verify = async () => {
  if (problemInput.value.length === 0 || solutionInput.value.length === 0) {
    setStatus(statusEl, "Provide both problem.json and solution.json", "error");
    return;
  }

  verifyBtn.disabled = true;
  setStatus(statusEl, "Running verify...", "pending");
  stdoutEl.textContent = "";
  stderrEl.textContent = "";
  exitCodeEl.textContent = "-";
  exitStatusEl.textContent = "-";

  try {
    const response = await fetch("/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        problem: problemInput.value,
        solution: solutionInput.value,
      }),
    });
    if (!response.ok) {
      const errorText = await response.text();
      setStatus(statusEl, `Backend error (${response.status}): ${errorText}`, "error");
      return;
    }
    const data = await response.json();
    renderResult(data, "json");
  } catch (err) {
    setStatus(statusEl, String(err), "error");
  } finally {
    verifyBtn.disabled = false;
  }
};

const summarizeWarnings = () => {
  const combined = [...state.translationWarnings, ...state.validationWarnings];
  if (combined.length === 0) return "No warnings.";
  const blocking = combined.filter((w) => w.severity === "error").length;
  if (blocking > 0) return `${blocking} blocking error(s).`;
  return `${combined.length} warning(s).`;
};

const renderWarnings = () => {
  const warnings = [...state.translationWarnings, ...state.validationWarnings];
  if (!warnings.length) {
    warningsPanel.style.display = "none";
    return;
  }
  warningsPanel.style.display = "block";
  warningsListEl.innerHTML = "";
  warnings.forEach((w) => {
    const row = document.createElement("div");
    row.className = `warning-row ${w.severity}`;
    const header = document.createElement("div");
    header.innerHTML = `<strong>${w.severity.toUpperCase()}</strong> ${w.code}`;
    const msg = document.createElement("div");
    msg.textContent = w.message;
    row.appendChild(header);
    row.appendChild(msg);
    if (w.assumption) {
      const assump = document.createElement("div");
      assump.className = "muted";
      assump.textContent = `Assumption: ${w.assumption}`;
      row.appendChild(assump);
    }
    if (w.field_path) {
      const path = document.createElement("div");
      path.className = "badge";
      path.textContent = w.field_path;
      row.appendChild(path);
    }
    warningsListEl.appendChild(row);
  });
};

const validateDraftLocally = () => {
  if (!state.draft) {
    state.validationWarnings = [];
    return;
  }
  const warnings = [];
  const vars = state.draft.variables || [];
  const seen = new Set();
  if (!vars.length) {
    warnings.push({ code: "no_variables", message: "Add at least one variable.", severity: "error", field_path: "variables" });
  }
  vars.forEach((v, idx) => {
    if (!v.id) warnings.push({ code: "empty_var", message: "Variable id required.", severity: "error", field_path: `variables[${idx}]` });
    if (seen.has(v.id)) warnings.push({ code: "duplicate_var", message: `Duplicate variable ${v.id}`, severity: "error", field_path: `variables[${idx}]` });
    seen.add(v.id);
  });

  const objective = state.draft.objective || {};
  if (!["min", "max"].includes(objective.sense)) {
    warnings.push({ code: "objective_sense", message: "Objective sense must be min or max.", severity: "error", field_path: "objective.sense" });
  }
  const hasObjectiveTerms =
    (objective.linear_terms && objective.linear_terms.length > 0) ||
    (objective.quadratic_terms && objective.quadratic_terms.length > 0);
  if (!hasObjectiveTerms) {
    warnings.push({ code: "objective_empty", message: "Add objective terms.", severity: "error", field_path: "objective" });
  }

  const constraints = state.draft.constraints || [];
  if (!constraints.length) {
    warnings.push({ code: "no_constraints", message: "Add at least one constraint.", severity: "error", field_path: "constraints" });
  } else {
    constraints.forEach((c, idx) => {
      if (!["<=", "==", ">="].includes(c.sense)) {
        warnings.push({ code: "invalid_constraint_sense", message: "Use <=, ==, or >=.", severity: "error", field_path: `constraints[${idx}].sense` });
      }
      if (!c.terms || c.terms.length === 0) {
        warnings.push({ code: "empty_constraint_terms", message: "Constraint needs terms.", severity: "error", field_path: `constraints[${idx}]` });
      }
    });
  }

  const candidate = state.draft.candidate_solution || [];
  if (!candidate.length) {
    warnings.push({ code: "missing_candidate", message: "Provide candidate solution values.", severity: "error", field_path: "candidate_solution" });
  } else {
    const missing = vars.filter((v) => !candidate.some((c) => c.var === v.id));
    if (missing.length) {
      warnings.push({ code: "candidate_incomplete", message: `Missing values for ${missing.map((m) => m.id).join(", ")}`, severity: "error", field_path: "candidate_solution" });
    }
  }
  state.validationWarnings = warnings;
};

const renderClarifications = () => {
  if (!state.needsClarification || state.clarificationQuestions.length === 0) {
    clarificationPanel.style.display = "none";
    return;
  }
  clarificationPanel.style.display = "block";
  clarificationList.innerHTML = "";
  state.clarificationQuestions.forEach((q) => {
    const li = document.createElement("li");
    li.textContent = q;
    clarificationList.appendChild(li);
  });
};

const renderBanner = () => {
  if (!state.draft) {
    draftBanner.style.display = "none";
    return;
  }
  draftBanner.style.display = "block";
  bannerSubcopy.textContent = summarizeWarnings();
};

const renderVariablesSection = (container) => {
  const section = document.createElement("div");
  const title = document.createElement("div");
  title.className = "section-title";
  title.textContent = "Variables";
  section.appendChild(title);

  const list = document.createElement("div");
  list.className = "edit-grid";
  state.draft.variables.forEach((v, idx) => {
    const row = document.createElement("div");
    row.className = "edit-row";
    const idInput = document.createElement("input");
    idInput.value = v.id || "";
    idInput.placeholder = "id";
    idInput.oninput = (e) => {
      state.draft.variables[idx].id = e.target.value.trim();
      refreshDraftUI();
    };
    const labelInput = document.createElement("input");
    labelInput.value = v.label || "";
    labelInput.placeholder = "label (optional)";
    labelInput.oninput = (e) => {
      state.draft.variables[idx].label = e.target.value;
    };
    const removeBtn = document.createElement("button");
    removeBtn.className = "ghost mini-btn";
    removeBtn.type = "button";
    removeBtn.textContent = "Remove";
    removeBtn.onclick = () => {
      state.draft.variables.splice(idx, 1);
      refreshDraftUI();
    };
    row.appendChild(idInput);
    row.appendChild(labelInput);
    row.appendChild(removeBtn);
    list.appendChild(row);
  });
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "ghost mini-btn";
  addBtn.textContent = "Add variable";
  addBtn.onclick = () => {
    const nextId = `x${state.draft.variables.length + 1}`;
    state.draft.variables.push({ id: nextId, label: "" });
    refreshDraftUI();
  };
  section.appendChild(list);
  section.appendChild(addBtn);
  container.appendChild(section);
};

const renderObjectiveSection = (container) => {
  const section = document.createElement("div");
  const title = document.createElement("div");
  title.className = "section-title";
  title.textContent = "Objective";
  section.appendChild(title);

  const senseSelect = document.createElement("select");
  senseSelect.value = state.draft.objective.sense || "min";
  ["min", "max"].forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    senseSelect.appendChild(opt);
  });
  senseSelect.onchange = (e) => {
    state.draft.objective.sense = e.target.value;
    refreshDraftUI();
  };
  section.appendChild(senseSelect);

  const linearTitle = document.createElement("div");
  linearTitle.className = "badge";
  linearTitle.textContent = "Linear terms";
  section.appendChild(linearTitle);

  const linearList = document.createElement("div");
  linearList.className = "edit-grid";
  (state.draft.objective.linear_terms || []).forEach((t, idx) => {
    const row = document.createElement("div");
    row.className = "edit-row";
    const varInput = document.createElement("input");
    varInput.value = t.var || "";
    varInput.placeholder = "var";
    varInput.oninput = (e) => {
      state.draft.objective.linear_terms[idx].var = e.target.value.trim();
    };
    const coeffInput = document.createElement("input");
    coeffInput.type = "number";
    coeffInput.value = t.coeff;
    coeffInput.placeholder = "coeff";
    coeffInput.oninput = (e) => {
      state.draft.objective.linear_terms[idx].coeff = parseFloat(e.target.value);
    };
    const removeBtn = document.createElement("button");
    removeBtn.className = "ghost mini-btn";
    removeBtn.type = "button";
    removeBtn.textContent = "Remove";
    removeBtn.onclick = () => {
      state.draft.objective.linear_terms.splice(idx, 1);
      refreshDraftUI();
    };
    row.appendChild(varInput);
    row.appendChild(coeffInput);
    row.appendChild(removeBtn);
    linearList.appendChild(row);
  });
  const addLinear = document.createElement("button");
  addLinear.type = "button";
  addLinear.className = "ghost mini-btn";
  addLinear.textContent = "Add linear term";
  addLinear.onclick = () => {
    state.draft.objective.linear_terms.push({ var: state.draft.variables[0]?.id || "", coeff: 1 });
    refreshDraftUI();
  };
  section.appendChild(linearList);
  section.appendChild(addLinear);

  const quadTitle = document.createElement("div");
  quadTitle.className = "badge";
  quadTitle.textContent = "Quadratic terms";
  section.appendChild(quadTitle);

  const quadList = document.createElement("div");
  quadList.className = "edit-grid";
  (state.draft.objective.quadratic_terms || []).forEach((t, idx) => {
    const row = document.createElement("div");
    row.className = "edit-row";
    const varI = document.createElement("input");
    varI.value = t.var_i || "";
    varI.placeholder = "var i";
    varI.oninput = (e) => {
      state.draft.objective.quadratic_terms[idx].var_i = e.target.value.trim();
    };
    const varJ = document.createElement("input");
    varJ.value = t.var_j || "";
    varJ.placeholder = "var j";
    varJ.oninput = (e) => {
      state.draft.objective.quadratic_terms[idx].var_j = e.target.value.trim();
    };
    const coeffInput = document.createElement("input");
    coeffInput.type = "number";
    coeffInput.value = t.coeff;
    coeffInput.placeholder = "coeff";
    coeffInput.oninput = (e) => {
      state.draft.objective.quadratic_terms[idx].coeff = parseFloat(e.target.value);
    };
    const removeBtn = document.createElement("button");
    removeBtn.className = "ghost mini-btn";
    removeBtn.type = "button";
    removeBtn.textContent = "Remove";
    removeBtn.onclick = () => {
      state.draft.objective.quadratic_terms.splice(idx, 1);
      refreshDraftUI();
    };
    row.appendChild(varI);
    row.appendChild(varJ);
    row.appendChild(coeffInput);
    row.appendChild(removeBtn);
    quadList.appendChild(row);
  });
  const addQuad = document.createElement("button");
  addQuad.type = "button";
  addQuad.className = "ghost mini-btn";
  addQuad.textContent = "Add quadratic term";
  addQuad.onclick = () => {
    state.draft.objective.quadratic_terms.push({ var_i: state.draft.variables[0]?.id || "", var_j: state.draft.variables[0]?.id || "", coeff: 0 });
    refreshDraftUI();
  };
  section.appendChild(quadList);
  section.appendChild(addQuad);
  container.appendChild(section);
};

const renderConstraintsSection = (container) => {
  const section = document.createElement("div");
  const title = document.createElement("div");
  title.className = "section-title";
  title.textContent = "Constraints";
  section.appendChild(title);

  state.draft.constraints.forEach((c, idx) => {
    const card = document.createElement("div");
    card.className = "input-block";
    const head = document.createElement("div");
    head.className = "block-header";
    const labelInput = document.createElement("input");
    labelInput.value = c.label || `c${idx}`;
    labelInput.placeholder = "label";
    labelInput.oninput = (e) => {
      state.draft.constraints[idx].label = e.target.value;
    };
    const senseSelect = document.createElement("select");
    ["<=", "==", ">="].forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      senseSelect.appendChild(opt);
    });
    senseSelect.value = c.sense;
    senseSelect.onchange = (e) => {
      state.draft.constraints[idx].sense = e.target.value;
    };
    const rhsInput = document.createElement("input");
    rhsInput.type = "number";
    rhsInput.value = c.rhs;
    rhsInput.placeholder = "rhs";
    rhsInput.oninput = (e) => {
      state.draft.constraints[idx].rhs = parseFloat(e.target.value);
    };
    head.appendChild(labelInput);
    head.appendChild(senseSelect);
    head.appendChild(rhsInput);
    card.appendChild(head);

    const termsList = document.createElement("div");
    termsList.className = "edit-grid";
    c.terms.forEach((t, jdx) => {
      const row = document.createElement("div");
      row.className = "edit-row";
      const varInput = document.createElement("input");
      varInput.value = t.var || "";
      varInput.placeholder = "var";
      varInput.oninput = (e) => {
        state.draft.constraints[idx].terms[jdx].var = e.target.value.trim();
      };
      const coeffInput = document.createElement("input");
      coeffInput.type = "number";
      coeffInput.value = t.coeff;
      coeffInput.placeholder = "coeff";
      coeffInput.oninput = (e) => {
        state.draft.constraints[idx].terms[jdx].coeff = parseFloat(e.target.value);
      };
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "ghost mini-btn";
      removeBtn.textContent = "Remove";
      removeBtn.onclick = () => {
        state.draft.constraints[idx].terms.splice(jdx, 1);
        refreshDraftUI();
      };
      row.appendChild(varInput);
      row.appendChild(coeffInput);
      row.appendChild(removeBtn);
      termsList.appendChild(row);
    });
    card.appendChild(termsList);
    const addTerm = document.createElement("button");
    addTerm.type = "button";
    addTerm.className = "ghost mini-btn";
    addTerm.textContent = "Add term";
    addTerm.onclick = () => {
      state.draft.constraints[idx].terms.push({ var: state.draft.variables[0]?.id || "", coeff: 1 });
      refreshDraftUI();
    };
    const removeConstraint = document.createElement("button");
    removeConstraint.type = "button";
    removeConstraint.className = "ghost mini-btn";
    removeConstraint.textContent = "Remove constraint";
    removeConstraint.onclick = () => {
      state.draft.constraints.splice(idx, 1);
      refreshDraftUI();
    };
    const actionsRow = document.createElement("div");
    actionsRow.className = "action-group";
    actionsRow.appendChild(addTerm);
    actionsRow.appendChild(removeConstraint);
    card.appendChild(actionsRow);
    section.appendChild(card);
  });
  const addConstraint = document.createElement("button");
  addConstraint.type = "button";
  addConstraint.className = "ghost mini-btn";
  addConstraint.textContent = "Add constraint";
  addConstraint.onclick = () => {
    state.draft.constraints.push({ label: `c${state.draft.constraints.length + 1}`, sense: "<=", terms: [], rhs: 0 });
    refreshDraftUI();
  };
  section.appendChild(addConstraint);
  container.appendChild(section);
};

const renderCandidateSection = (container) => {
  const section = document.createElement("div");
  const title = document.createElement("div");
  title.className = "section-title";
  title.textContent = "Proposed solution";
  section.appendChild(title);

  const list = document.createElement("div");
  list.className = "edit-grid";
  state.draft.candidate_solution.forEach((s, idx) => {
    const row = document.createElement("div");
    row.className = "edit-row";
    const varInput = document.createElement("input");
    varInput.value = s.var || "";
    varInput.placeholder = "var";
    varInput.oninput = (e) => {
      state.draft.candidate_solution[idx].var = e.target.value.trim();
    };
    const valSelect = document.createElement("select");
    [0, 1].forEach((val) => {
      const opt = document.createElement("option");
      opt.value = val;
      opt.textContent = val;
      valSelect.appendChild(opt);
    });
    valSelect.value = s.value;
    valSelect.onchange = (e) => {
      state.draft.candidate_solution[idx].value = Number(e.target.value);
    };
    const removeBtn = document.createElement("button");
    removeBtn.className = "ghost mini-btn";
    removeBtn.type = "button";
    removeBtn.textContent = "Remove";
    removeBtn.onclick = () => {
      state.draft.candidate_solution.splice(idx, 1);
      refreshDraftUI();
    };
    row.appendChild(varInput);
    row.appendChild(valSelect);
    row.appendChild(removeBtn);
    list.appendChild(row);
  });
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "ghost mini-btn";
  addBtn.textContent = "Add assignment";
  addBtn.onclick = () => {
    state.draft.candidate_solution.push({ var: state.draft.variables[0]?.id || "", value: 0 });
    refreshDraftUI();
  };
  section.appendChild(list);
  section.appendChild(addBtn);
  container.appendChild(section);
};

const renderMetadataSection = (container) => {
  const section = document.createElement("div");
  const title = document.createElement("div");
  title.className = "section-title";
  title.textContent = "Metadata";
  section.appendChild(title);
  const meta = state.draft.metadata || {};
  const metaBlock = document.createElement("div");
  metaBlock.className = "muted";
  metaBlock.textContent = `draft_version=${meta.draft_version} • created_at=${meta.created_at} • source_text_hash=${meta.source_text_hash}`;
  section.appendChild(metaBlock);
  container.appendChild(section);
};

const renderDraftEditor = () => {
  if (!state.draft) {
    draftEditor.style.display = "none";
    approvalActions.style.display = "none";
    return;
  }
  draftEditor.style.display = "block";
  draftSections.innerHTML = "";
  renderVariablesSection(draftSections);
  renderObjectiveSection(draftSections);
  renderConstraintsSection(draftSections);
  renderCandidateSection(draftSections);
  renderMetadataSection(draftSections);

  approvalActions.style.display = "flex";
  const blockingErrors = state.validationWarnings.some((w) => w.severity === "error");
  approveVerifyBtn.disabled = blockingErrors || state.approvalInFlight;
  downloadJsonBtn.disabled = !state.lastInternalProblem;
  const statusText = blockingErrors ? "Fix errors before approval." : "Ready to approve.";
  setStatus(approvalStatus, statusText, blockingErrors ? "error" : "pending");
};

const refreshDraftUI = () => {
  validateDraftLocally();
  renderWarnings();
  renderClarifications();
  renderBanner();
  renderDraftEditor();
};

const draftFromText = async () => {
  const text = draftTextInput.value.trim();
  if (!text) {
    setStatus(draftStatus, "Provide problem description text.", "error");
    return;
  }
  draftGenerateBtn.disabled = true;
  setStatus(draftStatus, "Drafting...", "pending");
  try {
    const response = await fetch("/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      const errorText = await response.text();
      setStatus(draftStatus, `Error (${response.status}): ${errorText}`, "error");
      draftGenerateBtn.disabled = false;
      return;
    }
    const data = await response.json();
    state.draft = data.structured_draft || {};
    state.draft.variables = state.draft.variables || [];
    state.draft.objective = state.draft.objective || { sense: "min", linear_terms: [], quadratic_terms: [] };
    state.draft.objective.linear_terms = state.draft.objective.linear_terms || [];
    state.draft.objective.quadratic_terms = state.draft.objective.quadratic_terms || [];
    state.draft.constraints = state.draft.constraints || [];
    state.draft.candidate_solution = state.draft.candidate_solution || [];
    state.draft.metadata = state.draft.metadata || {};
    state.translationWarnings = Array.isArray(data.warnings) ? data.warnings : [];
    state.needsClarification = Boolean(data.needs_clarification);
    state.clarificationQuestions = data.clarification_questions || [];
    draftResults.style.display = "none";
    state.lastInternalProblem = "";
    state.lastInternalSolution = "";
    setStatus(draftStatus, "Draft ready. Review before approval.", "pending");
    refreshDraftUI();
  } catch (err) {
    setStatus(draftStatus, String(err), "error");
  } finally {
    draftGenerateBtn.disabled = false;
  }
};

const approveAndVerify = async () => {
  if (!state.draft) return;
  validateDraftLocally();
  const blockingErrors = state.validationWarnings.some((w) => w.severity === "error");
  if (blockingErrors) {
    refreshDraftUI();
    return;
  }
  approveVerifyBtn.disabled = true;
  state.approvalInFlight = true;
  setStatus(approvalStatus, "Running verifier...", "pending");
  try {
    const response = await fetch("/approve_and_verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        structured_draft: state.draft,
        run_options: { compare_solvers: compareSolversToggle.checked },
      }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      state.translationWarnings = Array.isArray(data.warnings) ? data.warnings : [];
      refreshDraftUI();
      setStatus(approvalStatus, data.error || "Verification blocked", "error");
      return;
    }
    const data = await response.json();
    state.lastInternalProblem = data.internal_problem_json || "";
    state.lastInternalSolution = data.internal_solution_json || "";
    renderResult(data, "draft");
    refreshDraftUI();
  } catch (err) {
    setStatus(approvalStatus, String(err), "error");
  } finally {
    approveVerifyBtn.disabled = false;
    state.approvalInFlight = false;
  }
};

const downloadInternalJson = () => {
  if (!state.lastInternalProblem || !state.lastInternalSolution) return;
  const zip = [
    { name: "problem.json", content: state.lastInternalProblem },
    { name: "solution.json", content: state.lastInternalSolution },
  ];
  zip.forEach((file) => {
    const blob = new Blob([file.content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = file.name;
    a.click();
    URL.revokeObjectURL(url);
  });
};

const rerunDraft = () => {
  state.draft = null;
  state.translationWarnings = [];
  state.validationWarnings = [];
  state.needsClarification = false;
  state.clarificationQuestions = [];
  draftResults.style.display = "none";
  refreshDraftUI();
  setStatus(draftStatus, "Awaiting draft", "idle");
};

tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});
loadExampleBtn.addEventListener("click", loadExamples);
verifyBtn.addEventListener("click", verify);
problemFileInput.addEventListener("change", () => readFileInto(problemFileInput, problemInput));
solutionFileInput.addEventListener("change", () => readFileInto(solutionFileInput, solutionInput));

draftGenerateBtn.addEventListener("click", draftFromText);
approveVerifyBtn.addEventListener("click", approveAndVerify);
rerunDraftBtn.addEventListener("click", rerunDraft);
downloadJsonBtn.addEventListener("click", downloadInternalJson);

setStatus(statusEl, "Idle");
setStatus(draftStatus, "Awaiting draft");
refreshDraftUI();
