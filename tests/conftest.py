"""Conftest."""

import pytest


@pytest.fixture
def my_test_number() -> int:
    """My test number.

    Returns:
        A really awesome number.
    """
    return 42
