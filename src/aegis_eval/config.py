import os

def get_db_url() -> str:
    """
    Resolve the database URL following configuration precedence:
    1. If USE_SQLITE=1 is set, always use SQLite. If DATABASE_URL is provided and is a sqlite URL, use it, otherwise fallback to sqlite:///aegis_eval.db.
    2. If USE_SQLITE is not set (or 0), use DATABASE_URL if provided.
    3. Fallback to postgresql://user:password@localhost:5432/postgres.
    """
    use_sqlite = os.environ.get("USE_SQLITE", "0") == "1"
    env_url = os.environ.get("DATABASE_URL")
    
    if use_sqlite:
        if env_url and env_url.startswith("sqlite://"):
            return env_url
        return "sqlite:///aegis_eval.db"
    
    if env_url:
        return env_url
        
    return "postgresql://user:password@localhost:5432/postgres"
