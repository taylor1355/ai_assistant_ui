"""Copy credentials from NPC project to virtual environment.

This script copies the credentials directory from the NPC project
to the virtual environment. It requires the NPC_PROJECT environment
variable to be set.
"""
import os
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
ENV_VAR = "NPC_PROJECT"
VENV_PATH = PROJECT_ROOT / ".venv"

def get_creds_dir() -> Path:
    """Get the path to the NPC credentials directory."""
    try:
        npc_project = Path(os.environ[ENV_VAR])
        return npc_project / "credentials"
    except KeyError:
        print(f"Error: {ENV_VAR} environment variable must be set", file=sys.stderr)
        sys.exit(1)

def main():
    """Main entry point."""
    source_dir = get_creds_dir()
    dest_dir = VENV_PATH / "lib" / "credentials"
    
    if not source_dir.exists():
        print(f"Error: Source credentials directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)
        
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
    print(f"Credentials copied successfully to {dest_dir}")

if __name__ == "__main__":
    main()
