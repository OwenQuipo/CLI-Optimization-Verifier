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
const problemFileInput = document.getElementById("problem-file");
const solutionFileInput = document.getElementById("solution-file");

const EXIT_STATUS = {
  0: "Feasible",
  1: "Infeasible",
};

const setStatus = (text, mode = "idle") => {
  statusEl.textContent = text;
  statusEl.classList.remove("ok", "error", "pending");
  if (mode === "ok") statusEl.classList.add("ok");
  if (mode === "error") statusEl.classList.add("error");
  if (mode === "pending") statusEl.classList.add("pending");
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
  setStatus("Loading examples...", "pending");
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
    setStatus("Examples loaded", "ok");
  } catch (err) {
    setStatus(String(err), "error");
  }
};

const renderResult = (data) => {
  const exitCode = typeof data.exitCode === "number" ? data.exitCode : -1;
  const label = EXIT_STATUS[exitCode] || "Error";
  exitCodeEl.textContent = exitCode;
  exitStatusEl.textContent = label;
  stdoutEl.textContent = data.stdout ?? "";
  stderrEl.textContent = data.stderr ?? "";
  if (data.stderr) {
    stderrSection.open = false;
    stderrSection.style.display = "";
  } else {
    stderrSection.open = false;
    stderrSection.style.display = "none";
  }

  if (exitCode === 0) {
    setStatus("Feasible (exit code 0)", "ok");
  } else if (exitCode === 1) {
    setStatus("Infeasible (exit code 1)", "error");
  } else {
    setStatus(`Error (exit code ${exitCode})`, "error");
  }
};

const verify = async () => {
  if (problemInput.value.length === 0 || solutionInput.value.length === 0) {
    setStatus("Provide both problem.json and solution.json", "error");
    return;
  }

  verifyBtn.disabled = true;
  setStatus("Running verify...", "pending");
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
      setStatus(`Backend error (${response.status}): ${errorText}`, "error");
      return;
    }
    const data = await response.json();
    renderResult(data);
  } catch (err) {
    setStatus(String(err), "error");
  } finally {
    verifyBtn.disabled = false;
  }
};

loadExampleBtn.addEventListener("click", loadExamples);
verifyBtn.addEventListener("click", verify);
problemFileInput.addEventListener("change", () => readFileInto(problemFileInput, problemInput));
solutionFileInput.addEventListener("change", () => readFileInto(solutionFileInput, solutionInput));

setStatus("Idle");
