import random

# Numerical tolerance for floating comparisons
TOL = 1e-9


def set_seed(value: int = 0) -> None:
    """Set deterministic seeds for modules that rely on randomness."""
    random.seed(value)
