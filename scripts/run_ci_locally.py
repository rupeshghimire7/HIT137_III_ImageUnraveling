"""
run_ci_locally.py

Runs the same checks as .github/workflows/ci.yml on your own computer, so
you know CI will pass BEFORE you push.

What it copies from the workflow
--------------------------------
* A clean checkout: the jobs run on a fresh copy of the repository, not
  on your working folder. By default that copy is your last commit
  (`git archive HEAD`), which is exactly what GitHub checks out - so a
  file that exists on your disk but was never committed (or is hidden
  by .gitignore) breaks the run here just as it would on GitHub.
* The three jobs, with the same commands:
    lint    - pip install ruff; ruff check src tests scripts
    imports - pip install -r requirements.txt (runtime deps ONLY);
              python -m compileall -q src tests scripts;
              python scripts/check_imports.py
    tests   - pip install -r requirements-dev.txt; python -m pytest -v,
              under xvfb-run when it is available (Linux), once for
              every Python version in the matrix (3.10, 3.11, 3.12)
* A fresh virtual environment for every job, so a package that only
  happens to be installed on your computer cannot hide a missing
  requirement. Environments are cached in ~/.cache/hit137-ci-local and
  rebuilt whenever the requirements file changes (or with --fresh).

What it cannot copy
-------------------
* The apt packages (libgl1, libglib2.0-0, xvfb) - install them yourself
  on Linux if OpenCV or xvfb-run is missing.
* Python versions you do not have installed are reported as SKIPPED.

Usage (from the project root)
-----------------------------
    python scripts/run_ci_locally.py               # check the last commit
    python scripts/run_ci_locally.py --uncommitted # check what `git add -A`
                                                   # would commit next
    python scripts/run_ci_locally.py --jobs lint imports
    python scripts/run_ci_locally.py --python 3.12 # only one test version
    python scripts/run_ci_locally.py --fresh       # rebuild the venvs

Exit status is 0 only when every job that ran passed.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path.home() / ".cache" / "hit137-ci-local"
MATRIX = ("3.10", "3.11", "3.12")   # tests job: python-version matrix
TOOLS_PYTHON = "3.12"                # lint and imports jobs
JOBS = ("lint", "imports", "tests")
LINT_TARGETS = ("src", "tests", "scripts")


class StepFailed(Exception):
    """A command inside a job exited with a non-zero status."""


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #
def banner(text: str) -> None:
    """Print a job heading."""
    print(f"\n{'=' * 72}\n  {text}\n{'=' * 72}", flush=True)


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    """Run one step, streaming its output. Raises StepFailed on error."""
    print(f"$ {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd, env=env, check=False)
    if result.returncode != 0:
        raise StepFailed(f"`{' '.join(command)}` exited with {result.returncode}")


def find_python(version: str) -> list[str] | None:
    """A command that starts Python `version` (e.g. "3.11"), or None if
    that version is not installed."""
    candidates = []
    if f"{sys.version_info.major}.{sys.version_info.minor}" == version:
        candidates.append([sys.executable])
    if shutil.which(f"python{version}"):
        candidates.append([f"python{version}"])
    if os.name == "nt" and shutil.which("py"):
        candidates.append(["py", f"-{version}"])
    if shutil.which("uv"):   # Pythons installed with `uv python install X.Y`
        found = subprocess.run(["uv", "python", "find", "--no-project", version],
                               capture_output=True, text=True, check=False)
        if found.returncode == 0 and found.stdout.strip():
            candidates.append([found.stdout.strip()])
    for command in candidates:
        probe = subprocess.run(
            [*command, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
            capture_output=True, text=True, check=False,
        )
        if probe.returncode == 0 and probe.stdout.strip() == version:
            return command
    return None


def venv_python(venv: Path) -> Path:
    """The python executable inside a virtual environment."""
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def make_venv(python: list[str], name: str, requirements: list[str], fresh: bool) -> Path:
    """Create (or reuse from the cache) a virtual environment with
    `requirements` installed, and return its python executable.

    `requirements` are pip arguments, e.g. ["-r", "/path/requirements.txt"]
    or ["ruff"]. The cache key includes the contents of any -r file, so
    editing a requirements file triggers a rebuild."""
    key = hashlib.sha256(" ".join(python).encode())
    for arg in requirements:
        # A requirements file counts by its contents, not its (temporary) path.
        key.update(Path(arg).read_bytes() if Path(arg).is_file() else arg.encode())
    venv = CACHE / f"{name}-{key.hexdigest()[:12]}"
    stamp = venv / ".installed"
    if fresh and venv.exists():
        shutil.rmtree(venv)
    if not stamp.exists():
        if venv.exists():
            shutil.rmtree(venv)   # half-built by an earlier, interrupted run
        venv.parent.mkdir(parents=True, exist_ok=True)
        run([*python, "-m", "venv", str(venv)], cwd=ROOT)
        pip = [str(venv_python(venv)), "-m", "pip", "install", "-q",
               "--disable-pip-version-check"]
        run([*pip, "--upgrade", "pip"], cwd=ROOT)
        run([*pip, *requirements], cwd=ROOT)
        stamp.write_text("ok")
    else:
        print(f"(reusing cached environment {venv.name})", flush=True)
    return venv_python(venv)


def checkout(uncommitted: bool, into: Path) -> None:
    """Copy the repository into `into`, like actions/checkout does.

    Default: the last commit (HEAD). With `uncommitted`: every file git
    would commit after `git add -A` - tracked files as they are now on
    disk plus new files that .gitignore does not hide."""
    if not uncommitted:
        archive = into / "head.tar"
        run(["git", "archive", "--format=tar", "-o", str(archive), "HEAD"], cwd=ROOT)
        with tarfile.open(archive) as tar:
            if sys.version_info >= (3, 12):
                tar.extractall(into, filter="data")
            else:
                tar.extractall(into)
        archive.unlink()
        return
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode().split("\0")
    for name in filter(None, listing):
        source = ROOT / name
        if source.is_file():   # skip files deleted from disk but not yet from git
            target = into / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


# ---------------------------------------------------------------------- #
# The three jobs from ci.yml
# ---------------------------------------------------------------------- #
def job_lint(repo: Path, fresh: bool) -> None:
    """Job "Lint (ruff)"."""
    python = find_python(TOOLS_PYTHON) or [sys.executable]
    py = make_venv(python, "lint", ["ruff"], fresh)
    # CI always installs the newest ruff, so keep the cached one current.
    run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check",
         "--upgrade", "ruff"], cwd=repo)
    run([str(py), "-m", "ruff", "check", "--output-format=concise", *LINT_TARGETS], cwd=repo)


def job_imports(repo: Path, fresh: bool) -> None:
    """Job "Import check" - with runtime requirements only."""
    requirements = repo / "requirements.txt"
    if not requirements.is_file():
        raise StepFailed("requirements.txt is not in the checkout (is it committed?)")
    python = find_python(TOOLS_PYTHON) or [sys.executable]
    py = make_venv(python, "imports", ["-r", str(requirements)], fresh)
    run([str(py), "-m", "compileall", "-q", *LINT_TARGETS], cwd=repo)
    run([str(py), "scripts/check_imports.py"], cwd=repo)


def job_tests(repo: Path, fresh: bool, version: str) -> None:
    """Job "Tests (Python <version>)"."""
    requirements = repo / "requirements-dev.txt"
    if not requirements.is_file():
        raise StepFailed(
            "requirements-dev.txt is not in the checkout - CI's "
            "`pip install -r requirements-dev.txt` would fail (is it committed, "
            "or hidden by .gitignore?)"
        )
    python = find_python(version)
    py = make_venv(python, f"tests-py{version}", ["-r", str(requirements)], fresh)
    command = [str(py), "-m", "pytest", "-v", "-p", "no:cacheprovider"]
    if shutil.which("xvfb-run"):
        command = ["xvfb-run", "-a", *command]
    elif sys.platform.startswith("linux"):
        print("NOTE: xvfb-run not found - GUI tests use your own display "
              "(or skip if there is none). Install it with: sudo apt install xvfb")
    run(command, cwd=repo)


# ---------------------------------------------------------------------- #
# Main
# ---------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("--uncommitted", action="store_true",
                        help="check the working folder as `git add -A` would commit it")
    parser.add_argument("--jobs", nargs="+", choices=JOBS, default=list(JOBS),
                        help="jobs to run (default: all)")
    parser.add_argument("--python", nargs="+", default=list(MATRIX), metavar="X.Y",
                        help="Python versions for the tests job (default: 3.10 3.11 3.12)")
    parser.add_argument("--fresh", action="store_true",
                        help="rebuild the cached virtual environments")
    parser.add_argument("--keep", action="store_true",
                        help="keep the temporary checkout and print where it is")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results: list[tuple[str, str, float]] = []
    workdir = Path(tempfile.mkdtemp(prefix="ci-local-"))
    repo = workdir / "repo"
    repo.mkdir()
    try:
        source = "working folder (as `git add -A` would commit it)" \
            if args.uncommitted else "last commit (HEAD)"
        banner(f"Checkout: {source}")
        checkout(args.uncommitted, repo)

        planned = []
        if "lint" in args.jobs:
            planned.append(("Lint (ruff)", lambda: job_lint(repo, args.fresh), None))
        if "imports" in args.jobs:
            planned.append(("Import check", lambda: job_imports(repo, args.fresh), None))
        if "tests" in args.jobs:
            for version in args.python:
                planned.append((
                    f"Tests (Python {version})",
                    lambda v=version: job_tests(repo, args.fresh, v),
                    version,
                ))

        for name, job, version in planned:
            banner(name)
            if version is not None and find_python(version) is None:
                print(f"Python {version} is not installed here - skipped.")
                results.append((name, "SKIPPED", 0.0))
                continue
            started = time.monotonic()
            try:
                job()
            except StepFailed as exc:
                print(f"\nFAILED: {exc}", flush=True)
                results.append((name, "FAILED", time.monotonic() - started))
            else:
                results.append((name, "passed", time.monotonic() - started))
    finally:
        if args.keep:
            print(f"\nCheckout kept in {repo}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)

    banner("Summary")
    for name, outcome, seconds in results:
        print(f"  {outcome:<8} {name:<24} {seconds:6.1f}s")
    failed = any(outcome == "FAILED" for _, outcome, _ in results)
    ran = any(outcome == "passed" for _, outcome, _ in results)
    if failed:
        print("\nSome jobs FAILED - GitHub CI would fail too. Fix them before pushing.")
        return 1
    if not ran:
        print("\nNothing ran.")
        return 1
    print("\nAll jobs that ran passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
