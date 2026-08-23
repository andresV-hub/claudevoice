import os
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


def normalize_windows_path(path):
    """
    Normaliza rutas para Windows.

    Evita que rutas procedentes de otros entornos
    (por ejemplo /home/...) lleguen a subprocess.
    """

    path = Path(path).expanduser()

    try:
        path = path.resolve()
    except Exception:
        path = Path(os.path.abspath(str(path)))

    return path


def find_git_root(path: Path):
    path = normalize_windows_path(path)

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(path),
                "rev-parse",
                "--show-toplevel",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )

        if result.returncode == 0:
            root = result.stdout.strip()

            if root:
                return normalize_windows_path(root)

    except Exception:
        pass

    return None


def find_project_root(start_path=None):

    if start_path is None:
        start_path = Path.cwd()

    current = normalize_windows_path(start_path)

    # Primero intentamos Git.
    git_root = find_git_root(current)

    if git_root and git_root.exists():
        return git_root

    # Después buscamos marcadores de proyecto.
    for directory in [current, *current.parents]:

        for marker in PROJECT_MARKERS:

            if "*" in marker:

                try:
                    if list(directory.glob(marker)):
                        return directory
                except Exception:
                    pass

            else:

                try:
                    if (directory / marker).exists():
                        return directory
                except Exception:
                    pass

    return current


def get_git_branch(project_dir: Path):

    project_dir = normalize_windows_path(project_dir)

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

    project_dir = normalize_windows_path(project_dir)

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

    if (
        list(project_dir.glob("*.sln"))
        or list(project_dir.glob("*.csproj"))
    ):
        detected.append(".NET")

    if not detected:
        detected.append("Proyecto")

    return detected


def get_project_info(start_path=None):

    root = find_project_root(start_path)

    # Protección adicional:
    # nunca devolver una ruta que no exista.
    if not root.exists():
        root = normalize_windows_path(Path.cwd())

    return {
        "root": root,
        "name": root.name,
        "branch": get_git_branch(root),
        "types": detect_project_type(root),
    }