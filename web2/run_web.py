
import os
import sys
from pathlib import Path
import subprocess

def main():
    web_dir = Path(__file__).parent
    app_file = web_dir / "app.py"

    if not app_file.exists():
        print(f"Error: Cannot find {app_file}")
        return

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_file),
        "--server.port", "8502",  # Use a different port
        "--server.address", "localhost",
    ]

    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=web_dir)

if __name__ == "__main__":
    main()
