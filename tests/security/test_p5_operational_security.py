import os
import re
import json
import pytest
from unittest.mock import patch, MagicMock

from aegis_eval.config import (
    get_db_url,
    sanitize_db_url,
    OperationalConfig,
    ConfigurationSecurityError
)
from aegis_eval.v4.api.middleware import (
    LogSanitizer,
    AuditLogger,
    require_auth_and_audit,
    global_rate_limiter
)
from aegis_eval.v4.authorizer import Authorizer
from aegis_eval.v4.state import QSem, ESem, CandidateAnswer, DecisionState

# ==============================================================================
# 1. Log Sanitizer & Secret Redaction Tests
# ==============================================================================

def test_log_sanitizer_redacts_bearer_tokens():
    raw = "Request failed with Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret"
    sanitized = LogSanitizer.sanitize_string(raw)
    assert "Bearer [REDACTED]" in sanitized
    assert "eyJhbGci" not in sanitized

def test_log_sanitizer_redacts_uri_passwords():
    raw_postgres = "Connected to postgresql://admin_user:SuperSecretPassword123!@db.internal:5432/aegis_prod"
    sanitized = LogSanitizer.sanitize_string(raw_postgres)
    assert "postgresql://admin_user:[REDACTED]@db.internal:5432/aegis_prod" in sanitized
    assert "SuperSecretPassword123!" not in sanitized

    raw_https = "Failed to fetch https://user:api_token_xyz@target.internal/v1/query"
    sanitized_https = LogSanitizer.sanitize_string(raw_https)
    assert "https://user:[REDACTED]@target.internal/v1/query" in sanitized_https
    assert "api_token_xyz" not in sanitized_https

def test_log_sanitizer_redacts_key_value_secrets():
    cases = [
        ('api_key="secret_token_12345"', "api_key=[REDACTED]"),
        ("token: 'secret_token_67890'", "token=[REDACTED]"),
        ("password=my_secret_pw", "password=[REDACTED]"),
        ("auth_token: special_access", "auth_token=[REDACTED]")
    ]
    for raw, expected in cases:
        sanitized = LogSanitizer.sanitize_string(raw)
        assert "[REDACTED]" in sanitized
        assert "secret_token" not in sanitized

def test_log_sanitizer_redacts_private_key_blocks():
    raw_pem = """
    -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEA0Y1+abcdefghijklmnopqrstuvwxyz1234567890
    -----END RSA PRIVATE KEY-----
    """
    sanitized = LogSanitizer.sanitize_string(raw_pem)
    assert "[REDACTED PRIVATE KEY]" in sanitized
    assert "MIIEowIBAAKCAQEA0Y1+" not in sanitized

def test_log_sanitizer_handles_nested_structures():
    nested = {
        "headers": {"Authorization": "Bearer token_abc123"},
        "connection": "postgresql://user:pass@host:5432/db",
        "nested_list": ["ok", "secret_key=xyz987"]
    }
    sanitized = LogSanitizer.sanitize(nested)
    assert sanitized["headers"]["Authorization"] == "Bearer [REDACTED]"
    assert "pass" not in sanitized["connection"]
    assert "[REDACTED]" in sanitized["nested_list"][1]

def test_audit_logger_sanitizes_exception_trace(monkeypatch):
    captured_logs = []
    monkeypatch.setattr("builtins.print", lambda msg: captured_logs.append(msg))
    
    global_rate_limiter.capacity = 100
    global_rate_limiter._buckets.clear()

    @require_auth_and_audit("test_target")
    def faulty_endpoint(req, principal):
        raise ConnectionError("Failed connecting to https://admin:LeakedPassword999@remote/query")

    with pytest.raises(ConnectionError):
        faulty_endpoint({}, "test_api_key_123")

    assert len(captured_logs) > 0
    raw_output = captured_logs[-1]
    parsed = json.loads(raw_output)

    assert parsed["decision"] == "REJECT"
    assert "LeakedPassword999" not in raw_output
    assert "[REDACTED]" in parsed["failure_reason"]


# ==============================================================================
# 2. Configuration & Fail-Closed Environment Tests
# ==============================================================================

def test_config_masks_database_url_credentials():
    url = "postgresql://aegis_user:top_secret_database_pw@localhost:5432/aegis"
    sanitized = sanitize_db_url(url)
    assert sanitized == "postgresql://aegis_user:[REDACTED]@localhost:5432/aegis"
    assert "top_secret_database_pw" not in sanitized

def test_config_fails_closed_in_production_without_db():
    with patch.dict(os.environ, {"AEGIS_ENV": "production"}, clear=True):
        with pytest.raises(ConfigurationSecurityError) as exc_info:
            get_db_url()
        assert "Production mode (AEGIS_ENV=production) mandates an explicitly configured DATABASE_URL" in str(exc_info.value)

def test_config_fails_closed_with_insecure_defaults_in_production():
    with patch.dict(os.environ, {
        "AEGIS_ENV": "production",
        "DATABASE_URL": "postgresql://user:password@localhost:5432/postgres"
    }, clear=True):
        with pytest.raises(ConfigurationSecurityError) as exc_info:
            get_db_url()
        assert "Insecure default credentials detected" in str(exc_info.value)

def test_operational_config_validates_production_api_secret():
    with patch.dict(os.environ, {
        "AEGIS_ENV": "production",
        "DATABASE_URL": "postgresql://valid_user:valid_pw@remote_host:5432/db",
        "AEGIS_API_SECRET": "too_short"
    }, clear=True):
        config = OperationalConfig()
        with pytest.raises(ConfigurationSecurityError) as exc_info:
            config.validate_production_invariants()
        assert "AEGIS_API_SECRET must be at least 32 characters" in str(exc_info.value)


# ==============================================================================
# 3. Static Container Hardening Tests
# ==============================================================================

def test_dockerfile_enforces_non_root_execution():
    assert os.path.exists("Dockerfile"), "Dockerfile must exist"
    with open("Dockerfile", "r", encoding="utf-8") as f:
        content = f.read()

    # Must specify non-root USER
    user_match = re.search(r'USER\s+(10001|aegis)', content)
    assert user_match is not None, "Dockerfile must enforce unprivileged non-root USER"

    # Must define HEALTHCHECK
    assert "HEALTHCHECK" in content, "Dockerfile must define HEALTHCHECK probe"

def test_docker_compose_enforces_immutability_and_capabilities():
    assert os.path.exists("docker-compose.yml"), "docker-compose.yml must exist"
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        content = f.read()

    # Verify read_only: true
    assert "read_only: true" in content, "docker-compose.yml must enforce read_only: true"

    # Verify security_opt no-new-privileges
    assert "no-new-privileges:true" in content, "docker-compose.yml must enforce no-new-privileges:true"

    # Verify cap_drop ALL
    assert "ALL" in content, "docker-compose.yml must drop all Linux capabilities (cap_drop: ALL)"


# ==============================================================================
# 4. Lifecycle & State Integrity Tests
# ==============================================================================

def test_authorizer_state_integrity_across_evaluation_batches():
    authorizer = Authorizer(validator_id="v4.1.0-operational-test")

    q1 = QSem(raw_query="query 1", constraints=["P1_mandatory"], status="CERTAIN", hash="q1_hash")
    e1 = ESem(raw_chunk="chunk 1", propositions=["P2_unrelated"], chunk_id="c1", status="CERTAIN", hash="e1_hash")
    cand1 = CandidateAnswer(answer_text="ans 1", claim_obligations=["P2_unrelated"], derivation_hash="d1_hash")

    # Cycle 1: Rejected evaluation (P1_mandatory not in propositions)
    res1 = authorizer.evaluate(q1, e1, cand1, [])
    assert res1.state == DecisionState.REJECT
    assert res1.grant is None
    assert len(res1.transition_trace) == 1

    # Cycle 2: Attempted repair laundering with replayed evidence (must raise violation)
    from aegis_eval.v4.authorizer import AuthorizationInvariantViolation
    e1_laundered = ESem(raw_chunk="chunk 1", propositions=["P1_mandatory"], chunk_id="c1", status="CERTAIN", hash="e1_hash_laundered")
    cand_repair = CandidateAnswer(answer_text="ans 1 repaired", claim_obligations=["P1_mandatory"], derivation_hash="d2_hash")
    
    with pytest.raises(AuthorizationInvariantViolation):
        authorizer.evaluate(q1, e1_laundered, cand_repair, res1.transition_trace)
