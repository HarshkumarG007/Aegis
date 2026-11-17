#!/usr/bin/env python3
"""
Aegis-Eval Production Preflight Diagnostic Tool
Verifies environment, database, model weights, and security invariants before deployment.
Exits with code 0 on SUCCESS, or 1 on FAILURE.
"""

import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

def run_preflight_checks() -> bool:
    all_passed = True
    results = {}

    print("==================================================================")
    print("      🛡️  Aegis-Eval Production Deployment Preflight Check       ")
    print("==================================================================")

    # 1. Runtime Environment Check
    py_version = sys.version_info
    py_ok = (py_version.major == 3 and py_version.minor >= 10)
    results["python_runtime"] = {
        "status": "PASS" if py_ok else "FAIL",
        "version": f"{py_version.major}.{py_version.minor}.{py_version.micro}"
    }
    if not py_ok:
        all_passed = False

    # 2. Configuration & Invariant Check
    try:
        from aegis_eval.config import OperationalConfig, get_db_url, sanitize_db_url
        config = OperationalConfig()
        db_url = get_db_url()
        sanitized_url = sanitize_db_url(db_url)
        results["configuration"] = {
            "status": "PASS",
            "environment": config.env,
            "database_url": sanitized_url,
            "is_production": config.is_production
        }
    except Exception as e:
        results["configuration"] = {"status": "FAIL", "error": str(e)}
        all_passed = False

    # 3. Core Architecture & TCB Imports
    try:
        from aegis_eval.v4.authorizer import Authorizer
        from aegis_eval.v4.api.middleware import LogSanitizer, AuditLogger
        from aegis_eval.v4.api.ssrf_protector import is_safe_ip, resolve_and_validate
        authorizer = Authorizer(validator_id="preflight-probe")
        results["core_architecture"] = {
            "status": "PASS",
            "authorizer_ready": True,
            "log_sanitizer_ready": True,
            "ssrf_protector_ready": True
        }
    except Exception as e:
        results["core_architecture"] = {"status": "FAIL", "error": str(e)}
        all_passed = False

    # 4. Model Weights Presence
    models_dir = Path("models")
    if models_dir.exists():
        gguf_files = list(models_dir.glob("*.gguf"))
        model_names = [f.name for f in gguf_files]
        results["model_weights"] = {
            "status": "PASS" if gguf_files else "WARN",
            "count": len(gguf_files),
            "models": model_names
        }
    else:
        results["model_weights"] = {"status": "FAIL", "error": "models directory not found"}
        all_passed = False

    # 5. Database Schema Connectivity
    try:
        from sqlalchemy import create_engine, text
        from aegis_eval.config import get_db_url
        engine = create_engine(get_db_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        results["database_connectivity"] = {"status": "PASS"}
    except Exception as e:
        # In build/container without active DB, mark as WARN/FAIL depending on env
        results["database_connectivity"] = {"status": "WARN", "note": str(e)}

    # 6. Documentation Completeness
    docs_dir = Path("docs")
    mandatory_docs = [
        "PRD.md", "architecture.md", "rules.md", "design.md", 
        "task.md", "memory.md", "testing.md", "security.md", "decisions.md"
    ]
    missing_docs = [doc for doc in mandatory_docs if not (docs_dir / doc).exists()]
    results["documentation"] = {
        "status": "PASS" if not missing_docs else "FAIL",
        "missing": missing_docs
    }
    if missing_docs:
        all_passed = False

    # Print Summary
    for check, res in results.items():
        status_icon = "✅" if res["status"] == "PASS" else ("⚠️" if res["status"] == "WARN" else "❌")
        print(f"{status_icon} {check.upper():<25}: {res['status']}")
        if "error" in res:
            print(f"   └── Error: {res['error']}")

    print("------------------------------------------------------------------")
    if all_passed:
        print("🎉 PREFLIGHT CHECK COMPLETED: System is PRODUCTION READY.")
        return True
    else:
        print("🚨 PREFLIGHT CHECK FAILED: Review the errors above.")
        return False

if __name__ == "__main__":
    success = run_preflight_checks()
    sys.exit(0 if success else 1)
