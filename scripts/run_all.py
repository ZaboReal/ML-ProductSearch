import subprocess
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, check=True)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)

    vector_backend = os.getenv("VECTOR_BACKEND", "pgvector").lower()
    print(f"Using vector backend: {vector_backend}")

    if vector_backend == "pgvector":
        print("[0/4] Setting up PostgreSQL with pgvector...")
        try:
            try:
                run(["docker-compose", "up", "-d", "postgres"])
            except (subprocess.CalledProcessError, FileNotFoundError):
                run(["docker", "compose", "up", "-d", "postgres"])
            
            print("Waiting for PostgreSQL to be ready...")
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    env = os.environ.copy()
                    env["PGPASSWORD"] = "postgres"
                    subprocess.run(
                        ["psql", "-h", "localhost", "-p", "5433", "-U", "postgres", "-d", "hinthint", "-c", "SELECT 1;"],
                        check=True, 
                        capture_output=True,
                        env=env
                    )
                    print("PostgreSQL is ready!")
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    if attempt == max_attempts - 1:
                        print("WARNING: PostgreSQL not ready after 60 seconds, continuing anyway...")
                    else:
                        time.sleep(2)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"WARNING: Failed to setup Docker PostgreSQL: {e}")
            print("Continuing - make sure PostgreSQL is running manually...")

    print("[1/4] Installing requirements...")
    try:
        run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError:
        print("Warning: Failed to install requirements. Continuing...")

    print("[2/4] Ingesting and normalizing data...")
    try:
        run([sys.executable, "src/ingest.py"])
    except subprocess.CalledProcessError:
        print("Warning: Ingestion script failed. Continuing...")

    print("[3/4] Generating embeddings and loading to vector store...")
    try:
        run([sys.executable, "src/embed_and_load.py"])
    except subprocess.CalledProcessError:
        print("Warning: Embedding script failed. Continuing...")

    print("[4/4] Starting app at http://127.0.0.1:8000...")
    try:
        run([sys.executable, "src/app.py"])
    except subprocess.CalledProcessError:
        print("Error: Failed to start app.")


if __name__ == "__main__":
    main()


