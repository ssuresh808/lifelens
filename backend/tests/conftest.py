"""Shared fixtures. Reset rate-limit and budget state so each test is isolated."""

import pytest

from app import main


@pytest.fixture(autouse=True)
def _reset_limiter_state():
    """Every test starts with a clean per-IP history and daily budget."""
    main._hits.clear()
    if hasattr(main, "_daily"):
        main._daily.clear()
    yield
    main._hits.clear()
    if hasattr(main, "_daily"):
        main._daily.clear()
