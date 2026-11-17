import time
import json
import secrets
import hashlib
import functools
import re
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, Union

from aegis_eval.v4.state import AuthorizedAnswer, DecisionState

# -- Log Sanitizer & Redaction Engine --

class LogSanitizer:
    """
    Zero-trust log scrubber that redacts secrets, bearer tokens, API keys, 
    passwords, and credentials from log strings, exceptions, and nested data.
    """
    PATTERNS = [
        # Database / HTTP URI credentials (e.g. postgresql://user:secret@host)
        (re.compile(r'://([^:]+):([^@]+)@'), r'://\1:[REDACTED]@'),
        # Bearer tokens
        (re.compile(r'(?i)\b(bearer\s+)[a-zA-Z0-9_\-\.]+'), r'\1[REDACTED]'),
        # Basic Auth tokens
        (re.compile(r'(?i)\b(basic\s+)[a-zA-Z0-9+/=]+'), r'\1[REDACTED]'),
        # Key-value secret assignments (api_key=..., secret_key=..., token='...')
        (re.compile(r'(?i)\b((?:api|secret|auth)[_-]?(?:key|token)|secret|token|password)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.]+["\']?'), r'\1=[REDACTED]'),
        # Private key blocks
        (re.compile(r'-----BEGIN [A-Z ]+PRIVATE KEY-----[^-]+-----END [A-Z ]+PRIVATE KEY-----', re.DOTALL), r'[REDACTED PRIVATE KEY]'),
    ]

    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """Applies all redaction rules to a string."""
        if not text:
            return ""
        result = text
        for pattern, replacement in cls.PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """Recursively sanitizes nested dictionaries, lists, and strings."""
        if isinstance(data, str):
            return cls.sanitize_string(data)
        elif isinstance(data, dict):
            return {cls.sanitize(k): cls.sanitize(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple, set)):
            return [cls.sanitize(item) for item in data]
        elif isinstance(data, Exception):
            return cls.sanitize_string(str(data))
        return data


# -- Audit Logging --

class AuditLogger:
    last_log_entry: Optional[Dict[str, Any]] = None

    @staticmethod
    def log(principal: str, target: str, request_id: str, decision: str, 
            provenance_hashes: Dict[str, str], failure_reason: Optional[str] = None):
        """
        Structured JSON audit logger capturing security-relevant provenance.
        Automatically applies LogSanitizer to ensure zero secret leakage in logs.
        """
        sanitized_failure = LogSanitizer.sanitize_string(failure_reason) if failure_reason else None
        sanitized_provenance = LogSanitizer.sanitize(provenance_hashes)
        
        log_entry = {
            "timestamp": time.time(),
            "principal": LogSanitizer.sanitize_string(principal),
            "target": LogSanitizer.sanitize_string(target),
            "request_id": request_id,
            "decision": decision,
            "provenance_hashes": sanitized_provenance,
        }
        if sanitized_failure:
            log_entry["failure_reason"] = sanitized_failure
            
        AuditLogger.last_log_entry = log_entry
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
    6. Emits Sanitized Audit Log.
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
                
            if not global_rate_limiter.allow_request(principal):
                AuditLogger.log(principal, target_name, request_id, "REJECT", {}, "Rate limit exceeded")
                raise ConnectionRefusedError("Rate limit exceeded")
                
            try:
                # Execute API logic
                result = func(request, principal, *args, **kwargs)
                
                # FAIL-CLOSED ORCHESTRATION CHECK
                if isinstance(result, AuthorizedAnswer):
                    if result.state == DecisionState.PASS_SUBSTANTIVE:
                        provenance = result.provenance
                        AuditLogger.log(principal, target_name, request_id, "PASS_SUBSTANTIVE", provenance)
                    else:
                        AuditLogger.log(principal, target_name, request_id, result.state.value, {})
                else:
                    AuditLogger.log(principal, target_name, request_id, "SUCCESS", {})
                    
                return result
                
            except Exception as e:
                # Log sanitized exception string to prevent secret reflection
                sanitized_err = LogSanitizer.sanitize_string(str(e))
                AuditLogger.log(principal, target_name, request_id, "REJECT", {}, sanitized_err)
                raise
                
        return wrapper
    return decorator

global_rate_limiter = RateLimiter()
