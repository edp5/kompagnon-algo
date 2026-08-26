import importlib
import os
import sys
from unittest.mock import patch, MagicMock


def test_postgres_url_rewritten_to_psycopg2():
    """
    Covers the `if DATABASE_URL.startswith("postgres://")` branch in session.py.
    When the env var starts with the legacy `postgres://` scheme, it must be
    rewritten to `postgresql+psycopg2://` so SQLAlchemy can connect.

    We isolate the rewrite logic by removing the cached module from sys.modules
    and patching create_engine/sessionmaker to avoid a real DB connection.
    """
    legacy_url = "postgres://user:pass@localhost:5432/testdb"
    expected_url = "postgresql+psycopg2://user:pass@localhost:5432/testdb"

    # Save and remove the already-imported module so the fresh import/reload
    # actually re-executes the module-level code under the patched env.
    saved = {k: v for k, v in sys.modules.items() if k.startswith("src.db.session")}
    for k in saved:
        del sys.modules[k]

    try:
        with patch.dict(os.environ, {"DATABASE_URL": legacy_url}, clear=False), \
             patch("sqlalchemy.create_engine", return_value=MagicMock()), \
             patch("sqlalchemy.orm.sessionmaker", return_value=MagicMock()):
            import src.db.session as session_module
            assert session_module.DATABASE_URL == expected_url
    finally:
        # Restore original modules so other tests are unaffected.
        for k in saved:
            sys.modules[k] = saved[k]
        # Remove the freshly-imported copy if it's still there.
        sys.modules.pop("src.db.session", None)
        for k, v in saved.items():
            sys.modules[k] = v

