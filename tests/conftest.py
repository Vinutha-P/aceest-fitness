"""Shared pytest fixtures for the ACEest test suite."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aceest import create_app  # noqa: E402
from aceest.db import get_db  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    """Provide a Flask app bound to a throwaway SQLite database."""
    database = tmp_path / "test_aceest.db"
    application = create_app(
        {"TESTING": True, "DATABASE": str(database), "SECRET_KEY": "test"}
    )
    yield application


@pytest.fixture()
def client(app):
    """Provide a Flask test client."""
    return app.test_client()


@pytest.fixture()
def runner(app):
    """Provide a CLI runner for testing Flask commands."""
    return app.test_cli_runner()


@pytest.fixture()
def db(app):
    """Provide a database connection inside an application context."""
    with app.app_context():
        yield get_db()
