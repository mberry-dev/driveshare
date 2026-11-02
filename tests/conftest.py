"""Shared fixtures: each test gets a fresh database seeded with the demo data."""
import os
import sys
import tempfile
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402

_tmpdir = tempfile.mkdtemp()
database.DATABASE = os.path.join(_tmpdir, 'test.db')

import app as app_module  # noqa: E402  (imports after DATABASE is redirected)


@pytest.fixture
def app(tmp_path):
    # A separate database file per test: Windows can't delete a file that is still open
    database.DATABASE = str(tmp_path / 'test.db')
    database.init_db()
    app_module.app.config.update(TESTING=True)
    yield app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_conn(app):
    import sqlite3
    conn = sqlite3.connect(database.DATABASE)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def login(client, email, password='password123'):
    return client.post('/login', data={'email': email, 'password': password},
                       follow_redirects=True)


def days_from_today(n):
    return (date.today() + timedelta(days=n)).isoformat()


@pytest.fixture
def make_client(app):
    """Return a logged-in client for the given demo email."""
    def _make(email, password='password123'):
        c = app.test_client()
        login(c, email, password)
        return c
    return _make
