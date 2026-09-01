import os
import pytest
from unittest.mock import patch
from aegis_eval.config import get_db_url

def test_db_config_use_sqlite_only():
    """When USE_SQLITE=1 is supplied, no PostgreSQL connection attempt occurs."""
    with patch.dict(os.environ, {"USE_SQLITE": "1"}, clear=True):
        url = get_db_url()
        assert url == "sqlite:///aegis_eval.db"
        assert "postgresql" not in url

def test_db_config_use_sqlite_with_database_url():
    """When USE_SQLITE=1 and DATABASE_URL=sqlite:///... are supplied, it uses the provided SQLite URL."""
    with patch.dict(os.environ, {"USE_SQLITE": "1", "DATABASE_URL": "sqlite:///custom.db"}, clear=True):
        url = get_db_url()
        assert url == "sqlite:///custom.db"
        assert "postgresql" not in url

def test_db_config_use_sqlite_overrides_postgres_url():
    """When USE_SQLITE=1 but DATABASE_URL points to postgres, it forces SQLite."""
    with patch.dict(os.environ, {"USE_SQLITE": "1", "DATABASE_URL": "postgresql://user:pass@localhost/db"}, clear=True):
        url = get_db_url()
        assert url == "sqlite:///aegis_eval.db"
        assert "postgresql" not in url

def test_db_config_no_sqlite_with_database_url():
    """When USE_SQLITE is not 1 and DATABASE_URL is provided, it uses DATABASE_URL."""
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://custom:custom@remote/db"}, clear=True):
        url = get_db_url()
        assert url == "postgresql://custom:custom@remote/db"

def test_db_config_fallback():
    """When nothing is provided, it falls back to the default postgres URL."""
    with patch.dict(os.environ, {}, clear=True):
        url = get_db_url()
        assert url == "postgresql://user:password@localhost:5432/postgres"
