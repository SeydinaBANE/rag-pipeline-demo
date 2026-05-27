from __future__ import annotations

import os
from collections.abc import Generator

import pytest

_TEST_SECRET = "change-me-in-production"  # noqa: S105


@pytest.fixture(autouse=True, scope="session")
def override_api_secret() -> Generator[None, None, None]:
    """Force the test API secret so JWT tokens generated in tests are valid.

    Without this, the local .env file's API__SECRET_KEY overrides the default
    and makes auth tests fail even though the secret matches in CI.
    """
    from src.config import get_settings

    original = os.environ.get("API__SECRET_KEY")
    os.environ["API__SECRET_KEY"] = _TEST_SECRET
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    if original is None:
        os.environ.pop("API__SECRET_KEY", None)
    else:
        os.environ["API__SECRET_KEY"] = original
