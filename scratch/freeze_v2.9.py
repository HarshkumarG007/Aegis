import hashlib
import json
import os

def hash_file(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def freeze():
    base_dir = os.path.join(os.path.dirname(__file__), "../src/aegis_eval/hardened_rag")
    gates_path = os.path.join(base_dir, "gates.py")
    extractor_path = os.path.join(base_dir, "condition_extractor.py")
    
    gates_hash = hash_file(gates_path)
    extractor_hash = hash_file(extractor_path)
    
    manifest = {
        "version": "v2.9_frozen",
        "gates.py_sha256": gates_hash,
        "condition_extractor.py_sha256": extractor_hash,
        "policy": "E+E0_proposition_bound",
        "description": "Frozen safety boundary for V3.0 End-to-End Utility Recovery."
    }
    
    report_dir = os.path.join(os.path.dirname(__file__), "../reports/benchmark-v2.9")
    os.makedirs(report_dir, exist_ok=True)
    out_path = os.path.join(report_dir, "freeze.json")
    
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Frozen V2.9 Safety Boundary: {out_path}")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    freeze()
