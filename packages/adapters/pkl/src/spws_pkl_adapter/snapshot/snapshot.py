"""Git-backed PKL content access: snapshot, working tree, optional remote mirror."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from spws_contracts_core.domain import ReadMode

WORKING_TREE_SHA = "WORKING_TREE"


@dataclass(frozen=True, slots=True)
class GitChange:
    relative_path: str
    status: str


class GitCommandError(RuntimeError):
    pass


def _run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitCommandError(f"git {' '.join(args)} failed: {stderr}")
    return result


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def repository_identity(repo: Path) -> str:
    result = _run_git(repo, "config", "--get", "remote.origin.url", check=False)
    remote = result.stdout.strip()
    if remote:
        return remote
    return str(repo.resolve())


FILESYSTEM_SHA = "FILESYSTEM"


class SnapshotReader:
    """Read PKL files via git show, working tree, filesystem fixtures, or optional bare mirror."""

    def __init__(
        self,
        repo_path: Path,
        *,
        read_mode: ReadMode | str = ReadMode.SNAPSHOT,
        commit: str | None = None,
        mirror_cache: Path | None = None,
        allow_remote: bool = False,
    ) -> None:
        self.repo_path = repo_path.resolve()
        mode_text = read_mode if isinstance(read_mode, str) else read_mode.value
        self._filesystem = mode_text == "filesystem" or not (self.repo_path / ".git").exists()
        if self._filesystem:
            self.read_mode = ReadMode.WORKING_TREE
        else:
            self.read_mode = ReadMode(read_mode) if isinstance(read_mode, str) else read_mode
        self.commit = commit
        self.mirror_cache = mirror_cache
        self.allow_remote = allow_remote
        if not self._filesystem and not (self.repo_path / ".git").exists():
            raise FileNotFoundError(f"not a git repository: {self.repo_path}")

    @property
    def repo_identity(self) -> str:
        if self._filesystem:
            return f"filesystem:{self.repo_path}"
        return repository_identity(self.repo_path)

    def resolve_commit(self) -> str:
        if self._filesystem:
            return FILESYSTEM_SHA
        if self.read_mode is ReadMode.WORKING_TREE:
            return WORKING_TREE_SHA
        if self.commit:
            return self.commit
        return _run_git(self.repo_path, "rev-parse", "HEAD").stdout.strip()

    def list_markdown_paths(self) -> list[str]:
        if self._filesystem:
            paths: list[str] = []
            for path in sorted(self.repo_path.rglob("*")):
                if path.is_file() and path.suffix.lower() in {".md", ".markdown"}:
                    paths.append(str(path.relative_to(self.repo_path)))
            return paths

        if self.read_mode is ReadMode.WORKING_TREE:
            result = _run_git(
                self.repo_path,
                "ls-files",
                "--",
                "*.md",
                "*.markdown",
            )
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]

        commit = self.resolve_commit()
        result = _run_git(
            self.repo_path,
            "ls-tree",
            "-r",
            "--name-only",
            commit,
            "--",
        )
        paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return [path for path in paths if path.endswith((".md", ".markdown"))]

    def read_bytes(self, relative_path: str) -> bytes:
        if self._filesystem or self.read_mode is ReadMode.WORKING_TREE:
            target = self.repo_path / relative_path
            if not target.is_file():
                raise FileNotFoundError(relative_path)
            return target.read_bytes()

        commit = self.resolve_commit()
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "show", f"{commit}:{relative_path}"],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise GitCommandError(result.stderr.decode("utf-8", errors="replace"))
        return result.stdout

    def diff_since(self, base_commit: str) -> list[GitChange]:
        head = self.resolve_commit()
        if head == WORKING_TREE_SHA:
            result = _run_git(
                self.repo_path,
                "diff",
                "--name-status",
                base_commit,
                "--",
                "*.md",
                "*.markdown",
            )
        else:
            result = _run_git(
                self.repo_path,
                "diff",
                "--name-status",
                base_commit,
                head,
                "--",
                "*.md",
                "*.markdown",
            )
        changes: list[GitChange] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status = parts[0].strip()
            path = parts[-1].strip()
            changes.append(GitChange(relative_path=path, status=status))
        return changes

    def ensure_remote_mirror(self, remote_url: str) -> Path:
        if not self.allow_remote:
            raise PermissionError("remote git reads disabled by policy")
        if self.mirror_cache is None:
            raise ValueError("mirror_cache path required for remote reads")
        safe_name = hashlib.sha256(remote_url.encode("utf-8")).hexdigest()[:16]
        mirror_path = self.mirror_cache / safe_name
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        if not mirror_path.exists():
            subprocess.run(
                ["git", "clone", "--mirror", remote_url, str(mirror_path)],
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            subprocess.run(
                ["git", "--git-dir", str(mirror_path), "remote", "update", "--prune"],
                capture_output=True,
                text=True,
                check=True,
            )
        return mirror_path
