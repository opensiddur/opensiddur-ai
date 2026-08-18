from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The sourcetexts and opensiddur-projects repositories are git submodules of this one,
# checked out at the repository root. Each keeps its content in a subdirectory.
SOURCETEXTS_ROOT = REPO_ROOT / "sourcetexts" / "sources"
PROJECT_DIRECTORY = REPO_ROOT / "opensiddur-projects" / "project"
INDEX_DB_DIRECTORY = REPO_ROOT / "database"
