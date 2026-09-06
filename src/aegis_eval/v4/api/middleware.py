import time
import json
import secrets
import hashlib
import functools
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any

from aegis_eval.v4.state import AuthorizedAnswer, DecisionState

# -- Audit Logging --

class AuditLogger:
    @staticmethod
    def log(principal: str, target: str, request_id: str, decision: str, 
            provenance_hashes: Dict[str, str], failure_reason: Optional[str] = None):
        """
        Structured JSON audit logger capturing security-relevant provenance.
        Does NOT log payloads or raw credentials.
        """
        log_entry = {
            "timestamp": time.time(),
            "principal": principal,
            "target": target,
            "request_id": request_id,
            "decision": decision,
            "provenance_hashes": provenance_hashes,
        }
        if failure_reason:
            log_entry["failure_reason"] = failure_reason
            
        print(json.dumps(log_entry))


# -- Rate Limiting --

@dataclass
class RateLimiter:
    """
    In-memory rate limiter (Token Bucket).
    NOTE: Non-authoritative for multi-worker/multi-instance deployments.
    Use a shared Redis/Memcached backend for production scaling.
    """
    capacity: int = 100
    refill_rate: float = 10.0 # tokens per second
    _buckets: Dict[str, float] = field(default_factory=dict)
    _last_refill: Dict[str, float] = field(default_factory=dict)

    def allow_request(self, principal: str) -> bool:
        now = time.time()
        
        # Initialize
        if principal not in self._buckets:
            self._buckets[principal] = self.capacity
            self._last_refill[principal] = now
            
        # Refill
        time_passed = now - self._last_refill[principal]
        self._buckets[principal] = min(self.capacity, self._buckets[principal] + time_passed * self.refill_rate)
        self._last_refill[principal] = now
        
        # Consume
        if self._buckets[principal] >= 1:
            self._buckets[principal] -= 1
            return True
        return False

# -- Authentication and Authorization --

# In a real app, this would be backed by a DB. 
# Storing hashes of API keys, NEVER plaintext.
VALID_API_KEY_HASHES = {
    # Hashed version of "test_api_key_123"
    "test_user": hashlib.sha256(b"test_api_key_123").hexdigest(),
    "limited_user": hashlib.sha256(b"limited_api_key_123").hexdigest()
}

# Principal -> Allowed Targets map
PRINCIPAL_AUTHORIZATION_MAP = {
    "test_user": ["target_A", "target_B", "test_target"],
    "limited_user": ["target_A"]
}

def authenticate(api_key: str) -> Optional[str]:
    """Verify API key using constant-time comparison against hashed values."""
    if not api_key:
        return None
        
    hashed_provided = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
    
    for principal, stored_hash in VALID_API_KEY_HASHES.items():
        if secrets.compare_digest(hashed_provided, stored_hash):
            return principal
    return None

def is_authorized(principal: str, target: str) -> bool:
    """Verify principal is authorized to access the specific target."""
    allowed_targets = PRINCIPAL_AUTHORIZATION_MAP.get(principal, [])
    return target in allowed_targets

# -- Orchestration Fail-Closed Enforcer --

def require_auth_and_audit(target_name: str):
    """
    Decorator to wrap API endpoints.
    1. Authenticates request.
    2. Authorizes principal for target.
    3. Enforces Rate Limits.
    4. Executes wrapped logic.
    5. Enforces that the API logic CANNOT manually mint a PASS_SUBSTANTIVE.
       It must return a valid AuthorizedAnswer created via Authorizer.
    6. Emits Audit Log.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(request: Any, api_key: str, *args, **kwargs):
            request_id = secrets.token_hex(8)
            principal = authenticate(api_key)
            
            if not principal:
                AuditLogger.log("UNAUTHENTICATED", target_name, request_id, "REJECT", {}, "Invalid or missing API key")
                raise PermissionError("Unauthenticated")
                
            if not is_authorized(principal, target_name):
                AuditLogger.log(principal, target_name, request_id, "REJECT", {}, "Principal not authorized for target")
                raise PermissionError("Unauthorized for this target")
                
            # Note: RateLimiter is a global singleton for this mock
            if not global_rate_limiter.allow_request(principal):
                AuditLogger.log(principal, target_name, request_id, "REJECT", {}, "Rate limit exceeded")
                raise ConnectionRefusedError("Rate limit exceeded")
                
            try:
                # Execute API logic
                result = func(request, principal, *args, **kwargs)
                
                # FAIL-CLOSED ORCHESTRATION CHECK
                # Ensure the API did not just return a fake object.
                # If the result claims PASS_SUBSTANTIVE, it MUST be a valid AuthorizedAnswer
                # with a valid grant (which is enforced by AuthorizedAnswer.__post_init__).
                if isinstance(result, AuthorizedAnswer):
                    if result.state == DecisionState.PASS_SUBSTANTIVE:
                        # Validation passes (the __post_init__ already validated the grant)
                        provenance = result.provenance
                        AuditLogger.log(principal, target_name, request_id, "PASS_SUBSTANTIVE", provenance)
                    else:
                        AuditLogger.log(principal, target_name, request_id, result.state.value, {})
                else:
                    # If it's just a standard API response (e.g. target registration), log success
                    AuditLogger.log(principal, target_name, request_id, "SUCCESS", {})
                    
                return result
                
            except Exception as e:
                # Any orchestration failure (e.g., provenance mismatch from Authorizer) fails closed
                AuditLogger.log(principal, target_name, request_id, "REJECT", {}, str(e))
                raise
                
        return wrapper
    return decorator

global_rate_limiter = RateLimiter()
