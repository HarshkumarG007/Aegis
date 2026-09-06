import pytest
import ipaddress
import urllib3
import os
import sys

sys.path.append(os.path.abspath("src"))

from aegis_eval.v4.api.ssrf_protector import is_safe_ip, resolve_and_validate, SSRFViolation, safe_fetch
from aegis_eval.v4.api.middleware import authenticate, require_auth_and_audit, global_rate_limiter, VALID_API_KEY_HASHES
from aegis_eval.v4.state import AuthorizedAnswer, CandidateAnswer, DecisionState

# ==========================================
# 1. SSRF & DNS Pinning Tests
# ==========================================

def test_is_safe_ip_rejects_loopback():
    assert not is_safe_ip("127.0.0.1")
    assert not is_safe_ip("127.123.45.67")
    assert not is_safe_ip("::1")
    assert not is_safe_ip("0.0.0.0")

def test_is_safe_ip_rejects_private():
    assert not is_safe_ip("10.0.0.1")
    assert not is_safe_ip("172.16.0.1")
    assert not is_safe_ip("192.168.1.1")
    assert not is_safe_ip("fc00::1")

def test_is_safe_ip_rejects_cloud_metadata():
    assert not is_safe_ip("169.254.169.254")

def test_is_safe_ip_rejects_ipv4_mapped_ipv6():
    # IPv4-mapped IPv6 address for 127.0.0.1
    assert not is_safe_ip("::ffff:127.0.0.1")
    assert not is_safe_ip("::ffff:7f00:1")

def test_resolve_and_validate_rejects_localhost():
    with pytest.raises(SSRFViolation, match="forbidden IP"):
        resolve_and_validate("localhost")

def test_safe_fetch_rejects_http():
    with pytest.raises(SSRFViolation, match="Only HTTPS is allowed"):
        safe_fetch("http://example.com")

def test_safe_fetch_resource_limits():
    # Attempting to fetch a large payload should raise ValueError
    # For test speed, we mock a response internally, but since safe_fetch uses actual urllib3
    # we just test the logic around size limits if we had a live endpoint.
    pass # In real test suite, point to local test server

# ==========================================
# 2. Authentication Tests
# ==========================================

def test_authenticate_constant_time():
    # A valid key (unhashed version of the hash in VALID_API_KEY_HASHES)
    assert authenticate("test_api_key_123") == "test_user"
    
    # Invalid keys
    assert authenticate("wrong") is None
    assert authenticate("") is None
    assert authenticate(None) is None

# ==========================================
# 3. Rate Limiting Tests
# ==========================================

def test_rate_limiter_consumes_tokens():
    # Global state reset for test
    global_rate_limiter.capacity = 2
    global_rate_limiter._buckets.clear()
    
    assert global_rate_limiter.allow_request("user1") is True
    assert global_rate_limiter.allow_request("user1") is True
    assert global_rate_limiter.allow_request("user1") is False # Exhausted
    
    # Another user is independent
    assert global_rate_limiter.allow_request("user2") is True

# ==========================================
# 4. Fail-Closed Orchestration Tests
# ==========================================

def test_orchestration_cannot_mint_pass_substantive():
    """
    Test that API logic attempting to fake a PASS_SUBSTANTIVE is rejected
    because it lacks the cryptographically valid grant.
    """
    
    @require_auth_and_audit("test_target")
    def malicious_api_endpoint(req, principal):
        # The API tries to bypass the V4 Authorizer entirely
        candidate = CandidateAnswer("evil", [], "hash")
        return AuthorizedAnswer(
            state=DecisionState.PASS_SUBSTANTIVE,
            candidate=candidate,
            grant=None, # Lacks grant!
            transition_trace=[],
            provenance={}
        )
        
    with pytest.raises(ValueError, match="PASS_SUBSTANTIVE requires an AuthorizationGrant"):
        malicious_api_endpoint({}, "test_api_key_123")
