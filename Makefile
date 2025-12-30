PYTHON ?= python3
VERIFY_BIN ?= ./bin/verify

.PHONY: verify-cli verify-ui prove-ui export-run demo test

verify-cli:
	$(VERIFY_BIN) examples/problem.json examples/solution.json

verify-ui:
	UI_VERSION=$${UI_VERSION:-ui-local} VERIFY_SAVE_FAILURES=$${VERIFY_SAVE_FAILURES:-0} $(PYTHON) backend/server.py

prove-ui:
	$(PYTHON) scripts/prove_ui_wrapper.py

export-run:
	$(PYTHON) -m src.run_bundle examples/problem.json examples/solution.json

demo:
	./scripts/demo.sh

test:
	pytest
