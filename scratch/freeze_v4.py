import hashlib
import json
import os
import subprocess
from datetime import datetime

def compute_dir_hash(dir_path):
    sha256 = hashlib.sha256()
    for root, _, files in os.walk(dir_path):
        for f in sorted(files):
            file_path = os.path.join(root, f)
            with open(file_path, "rb") as file:
                while chunk := file.read(8192):
                    sha256.update(chunk)
    return sha256.hexdigest()

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "unknown"

def main():
    print("Freezing V4 Architecture Provenance...")
    v4_dir = os.path.abspath("src/aegis_eval/v4")
    tests_dir = os.path.abspath("tests/security")
    
    provenance = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "git_commit": get_git_commit(),
        "v4_source_hash": compute_dir_hash(v4_dir) if os.path.exists(v4_dir) else "missing",
        "security_tests_hash": compute_dir_hash(tests_dir) if os.path.exists(tests_dir) else "missing",
        "experiment_name": "P2 Independent Generalization — Single-Model-Family",
        "model_family_limitation": "Attacker, Generator, and Adjudicator rely on local model environments."
    }
    
    out_path = "reports/benchmark-v4.1-p2/v4_frozen_provenance.json"
    with open(out_path, "w") as f:
        json.dump(provenance, f, indent=2)
        
    print(f"V4 Frozen. Provenance written to {out_path}")
    print(json.dumps(provenance, indent=2))

if __name__ == "__main__":
    main()
