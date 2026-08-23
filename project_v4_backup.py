import subprocess
from pathlib import Path


PROJECT_MARKERS = (
    ".git",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "*.sln",
    "*.csproj",
)


def find_git_root(path: Path):
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )

        if result.returncode == 0:
            root = result.stdout.strip()
            if root:
                return Path(root)

    except Exception:
        pass

    return None


def find_project_root(start_path=None):
    if start_path is None:
        start_path = Path.cwd()

    current = Path(start_path).resolve()

    git_root = find_git_root(current)

    if git_root:
        return git_root

    for directory in [current, *current.parents]:
        for marker in PROJECT_MARKERS:
            if "*" in marker:
                if list(directory.glob(marker)):
                    return directory
            elif (directory / marker).exists():
                return directory

    return current


def get_git_branch(project_dir: Path):
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(project_dir),
                "branch",
                "--show-current",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )

        if result.returncode == 0:
            branch = result.stdout.strip()
            return branch or "HEAD"

    except Exception:
        pass

    return None


def detect_project_type(project_dir: Path):
    detected = []

    if (project_dir / "package.json").exists():
        detected.append("Node.js")

    if (
        (project_dir / "tsconfig.json").exists()
        or list(project_dir.glob("*.ts"))
    ):
        detected.append("TypeScript")

    if (
        (project_dir / "pyproject.toml").exists()
        or (project_dir / "requirements.txt").exists()
        or list(project_dir.glob("*.py"))
    ):
        detected.append("Python")

    if (project_dir / "Gemfile").exists():
        detected.append("Ruby")

    if (project_dir / "Cargo.toml").exists():
        detected.append("Rust")

    if (project_dir / "go.mod").exists():
        detected.append("Go")

    if (
        (project_dir / "pom.xml").exists()
        or (project_dir / "build.gradle").exists()
    ):
        detected.append("Java")

    if list(project_dir.glob("*.sln")) or list(project_dir.glob("*.csproj")):
        detected.append(".NET")

    if not detected:
        detected.append("Proyecto")

    return detected


def get_project_info(start_path=None):
    root = find_project_root(start_path)

    return {
        "root": root,
        "name": root.name,
        "branch": get_git_branch(root),
        "types": detect_project_type(root),
    }