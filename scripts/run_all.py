import subprocess
import sys
import os
from pathlib import Path


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, check=True)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)

    # 1) Ensure dependencies are installed (best-effort)
    try:
        run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError:
        print("Warning: Failed to install requirements. Continuing...")

    # 2) Ingest and preprocess data (only needed for in-memory flow)
    try:
        run([sys.executable, "src/ingest.py"])
    except subprocess.CalledProcessError:
        print("Warning: Ingestion script failed. Continuing...")

    # 3) Generate embeddings and upsert to Pinecone (if configured) or in-memory
    try:
        run([sys.executable, "src/embed_and_load.py"])
    except subprocess.CalledProcessError:
        print("Warning: Embedding script failed. Continuing...")

    # 4) Launch the web app
    try:
        run([sys.executable, "src/app.py"])
    except subprocess.CalledProcessError:
        print("Error: Failed to start app.")


if __name__ == "__main__":
    main()


