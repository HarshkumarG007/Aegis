import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, os.path.abspath("."))
from scripts.preflight_check import run_preflight_checks

def test_package_version_bump():
    """Verify pyproject.toml defines version 4.2.0 for the production release."""
    with open("pyproject.toml", "r", encoding="utf-8") as f:
        content = f.read()
    assert 'version = "4.2.0"' in content, "pyproject.toml must be bumped to 4.2.0"

def test_env_example_template_completeness():
    """Verify .env.example exists, defines required production keys, and contains zero active secrets."""
    assert os.path.exists(".env.example"), ".env.example must exist"
    with open(".env.example", "r", encoding="utf-8") as f:
        content = f.read()

    # Required variables
    assert "AEGIS_ENV=" in content
    assert "DATABASE_URL=" in content
    assert "AEGIS_API_SECRET=" in content
    assert "PORT=" in content

    # Zero plaintext production passwords
    assert "SuperSecret" not in content
    assert "CHANGE_ME" in content

def test_preflight_check_passes():
    """Verify that the production deployment preflight script executes successfully."""
    success = run_preflight_checks()
    assert success is True, "Production preflight check must pass with return code True"

def test_canonical_documentation_integrity():
    """Verify that all 9 canonical living documents exist in docs/ and are non-empty."""
    docs_dir = Path("docs")
    mandatory_docs = [
        "PRD.md", "architecture.md", "rules.md", "design.md",
        "task.md", "memory.md", "testing.md", "security.md", "decisions.md"
    ]
    for doc in mandatory_docs:
        doc_path = docs_dir / doc
        assert doc_path.exists(), f"Mandatory document {doc} missing in docs/"
        assert doc_path.stat().st_size > 500, f"Document {doc} must be substantial (>500 bytes)"

def test_release_notes_manifest_coverage():
    """Verify RELEASE_NOTES.md documents V4.2.0 production release and gates P0-P7."""
    with open("RELEASE_NOTES.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "V4.2.0" in content
    assert "Gate P0" in content
    assert "Gate P3" in content
    assert "Gate P5" in content
    assert "Gate P6" in content
    assert "Gate P7" in content

def test_model_provenance_documentation_complete():
    """Verify docs/MODEL_PROVENANCE.md documents cryptographic weights as TCB."""
    provenance_path = Path("docs/MODEL_PROVENANCE.md")
    assert provenance_path.exists()
    content = provenance_path.read_text(encoding="utf-8")
    assert "SHA-256" in content
    assert "Trusted Computing Base" in content
