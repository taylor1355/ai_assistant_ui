"""Generate requirements.txt and set NPC_PROJECT environment variable.

This script:
1. Locates the NPC project directory (from env var or sibling directory)
2. Sets the NPC_PROJECT environment variable
3. Generates requirements.txt from template
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
ENV_VAR = "NPC_PROJECT"
def get_path_from_env(env_var: str) -> Path | None:
    """Get project path from environment variable if valid."""
    if path_str := os.environ.get(env_var):
        path = Path(path_str)
        return path if path.exists() else None
    return None

def find_sibling_project(parent_dir: Path, project_name: str) -> Path | None:
    """Find project in sibling directories."""
    sibling_path = parent_dir / project_name
    return sibling_path if sibling_path.exists() else None

def get_project_path(env_var: str, project_name: str, search_dir: Path) -> Path:
    """Get project path from environment variable or sibling directory."""
    if project_path := (get_path_from_env(env_var) or 
                       find_sibling_project(search_dir, project_name)):
        return project_path
    
    print(f"Error: Could not find {project_name} project directory.", file=sys.stderr)
    print(f"Either set {env_var} environment variable or ensure '{project_name}' exists "
          "as a sibling directory.", file=sys.stderr)
    sys.exit(1)

def set_env_var(env_var: str, path: Path) -> None:
    """Set environment variable if not already set."""

def generate_requirements(project_root: Path, placeholder_map: dict[str, str]) -> None:
    """Generate requirements.txt from template by substituting placeholders with actual values."""
    template_path = project_root / "requirements.txt.template"
    requirements_path = project_root / "requirements.txt"
    
    if not template_path.exists():
        print("Error: requirements.txt.template not found", file=sys.stderr)
        sys.exit(1)
        
    requirements_content = template_path.read_text()
    requirements_content = requirements_content.format(**placeholder_map)
    requirements_path.write_text(requirements_content)
    
    print(f"Generated requirements.txt with replacements: {placeholder_map}")

def main():
    """Main entry point."""
    npc_path = get_project_path(
        env_var=ENV_VAR,
        project_name="npc",
        search_dir=PROJECT_ROOT.parent
    )
    if ENV_VAR not in os.environ:
        os.environ[ENV_VAR] = str(npc_path)
    generate_requirements(
        project_root=PROJECT_ROOT,
        placeholder_map={ENV_VAR: str(npc_path)}
    )

if __name__ == "__main__":
    main()
