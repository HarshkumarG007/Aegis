import os
from huggingface_hub import hf_hub_download

print("Downloading Mistral-7B-Instruct-v0.2 GGUF...")
path = hf_hub_download(
    repo_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    filename="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    local_dir="models",
    local_dir_use_symlinks=False
)
print(f"Downloaded to {path}")
