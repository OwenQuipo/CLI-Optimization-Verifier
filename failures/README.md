# Failure bundles

- Set `VERIFY_SAVE_FAILURES=1` when running the UI server to automatically archive any non-zero CLI runs.
- Bundles are stored here as `.tar.gz` archives containing inputs, raw stdout/stderr, exit code, validation warnings (if any), and version metadata.
- Archives are append-only; do not edit them in place. Use them as regression seeds and demo artifacts.
