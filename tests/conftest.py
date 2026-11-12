import pytest


@pytest.fixture(scope="session")
def base_url() -> None:
    """Replace pytest-playwright's built-in base_url fixture, which pytest deprecates.
    Each GUI test serves its own game on a free port and passes the full URL itself."""
    return
