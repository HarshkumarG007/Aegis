import os
import sys
import hashlib
import requests
from sqlalchemy import create_engine, text
from aegis_eval.data.schema import Base
from aegis_eval.data.manifest import BenchmarkManifest

class PreflightError(Exception):
    pass

def verify_model_hash(model_path: str, expected_hash: str = None) -> bool:
    if not os.path.exists(model_path):
        raise PreflightError(f"Model file {model_path} not found.")
        
    if not expected_hash:
        print(f"WARN: No expected SHA-256 hash provided for model {model_path}. Reproducibility cannot be guaranteed.")
        return True
        
    print(f"Verifying hash for {model_path}...")
    sha256_hash = hashlib.sha256()
    with open(model_path, "rb") as f:
        # Read in chunks to avoid memory issues with large models
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            
    calculated_hash = sha256_hash.hexdigest()
    if calculated_hash != expected_hash:
        raise PreflightError(f"Hash mismatch for {model_path}! Expected: {expected_hash}, Got: {calculated_hash}")
        
    return True

def initialize_database():
    from aegis_eval.config import get_db_url
    db_url = get_db_url()
    print(f"Preflight: Initializing database at {db_url.split('@')[-1] if '@' in db_url else db_url}")
    
    try:
        engine = create_engine(db_url)
        with engine.begin() as conn:
            if db_url.startswith("postgresql"):
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                except Exception as e:
                    raise PreflightError(f"Failed to create pgvector extension. Ensure PostgreSQL has pgvector installed. Error: {e}")
        Base.metadata.create_all(engine)
    except PreflightError:
        raise
    except Exception as e:
        raise PreflightError(f"Database initialization failed: {e}")
        
def verify_target(target_url: str):
    if target_url == "reference":
        return
        
    print(f"Preflight: Checking target availability at {target_url}...")
    try:
        # Just check if it responds, don't validate semantics yet
        # The target might require a specific schema, but a basic GET or empty POST should return an HTTP response (even 4xx/5xx).
        # Since Aegis uses POST for queries, we'll send a dummy query.
        res = requests.post(target_url, json={"query": "ping", "query_id": "0"}, timeout=15)
        # Any response means the daemon is up
    except requests.RequestException as e:
        raise PreflightError(f"Target unavailable: {e}")

def run_preflight(target_url: str, manifest: BenchmarkManifest = None):
    print("Starting Preflight Checks...")
    
    # 1. DB Check
    initialize_database()
    
    # 2. Target Check
    verify_target(target_url)
    
    # 3. Model Check
    if manifest and hasattr(manifest, 'models') and manifest.models:
        model_path = manifest.models
        expected_hash = getattr(manifest, 'model_sha256', None) # We might not have it in V2 schema yet, but prepared for it
        verify_model_hash(model_path, expected_hash)
        
    print("Preflight checks passed!")
