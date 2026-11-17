import os
import re
from typing import Optional, Dict, Any

class ConfigurationSecurityError(Exception):
    """Raised when configuration validation detects an insecure or missing operational setting."""
    pass

def sanitize_db_url(url: str) -> str:
    """
    Sanitizes database URLs by masking embedded credentials for safe logging.
    e.g. postgresql://user:secret@host:5432/db -> postgresql://user:[REDACTED]@host:5432/db
    """
    if not url:
        return ""
    # Mask credentials between :// and @
    return re.sub(r'://([^:]+):([^@]+)@', r'://\1:[REDACTED]@', url)

def get_db_url() -> str:
    """
    Resolve the database URL following configuration precedence:
    1. If USE_SQLITE=1 is set, always use SQLite. If DATABASE_URL is provided and is a sqlite URL, use it, otherwise fallback to sqlite:///aegis_eval.db.
    2. If USE_SQLITE is not set (or 0), use DATABASE_URL if provided.
    3. Fallback to postgresql://user:password@localhost:5432/postgres (in non-production).
    
    In production mode (AEGIS_ENV=production), fallback to default credentials raises ConfigurationSecurityError.
    """
    aegis_env = os.environ.get("AEGIS_ENV", "development").lower()
    use_sqlite = os.environ.get("USE_SQLITE", "0") == "1"
    env_url = os.environ.get("DATABASE_URL")
    
    if use_sqlite:
        if env_url and env_url.startswith("sqlite://"):
            return env_url
        return "sqlite:///aegis_eval.db"
    
    if env_url:
        # In production, disallow obvious insecure placeholder credentials
        if aegis_env == "production" and "user:password" in env_url:
            raise ConfigurationSecurityError(
                "Insecure default credentials detected in DATABASE_URL during production mode."
            )
        return env_url
        
    if aegis_env == "production":
        raise ConfigurationSecurityError(
            "Production mode (AEGIS_ENV=production) mandates an explicitly configured DATABASE_URL. "
            "Refusing to fall back to hardcoded development credentials."
        )
        
    return "postgresql://user:password@localhost:5432/postgres"

class OperationalConfig:
    """
    Validates operational runtime configuration, fail-closed security invariants,
    and credential sanitization.
    """
    def __init__(self, env: Optional[str] = None):
        self.env = (env or os.environ.get("AEGIS_ENV", "development")).lower()
        self.is_production = self.env == "production"
        self.db_url = get_db_url()
        self.sanitized_db_url = sanitize_db_url(self.db_url)
        self.api_secret = os.environ.get("AEGIS_API_SECRET", "")
        
    def validate_production_invariants(self) -> None:
        """Enforces mandatory operational security checks for production environments."""
        if not self.is_production:
            return
            
        # 1. Database URL must not be default sqlite or unauthenticated postgres
        if "sqlite" in self.db_url and not os.environ.get("ALLOW_SQLITE_IN_PRODUCTION") == "1":
            raise ConfigurationSecurityError(
                "SQLite is prohibited in production without explicit ALLOW_SQLITE_IN_PRODUCTION=1 override."
            )
            
        if "user:password" in self.db_url:
            raise ConfigurationSecurityError(
                "Insecure development credentials ('user:password') detected in production database configuration."
            )
            
        # 2. API Secret requirement
        if not self.api_secret or len(self.api_secret) < 32:
            raise ConfigurationSecurityError(
                "AEGIS_API_SECRET must be at least 32 characters in production mode."
            )
