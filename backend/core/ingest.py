"""
M1 — Clone a public GitHub repo to a temporary directory.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# Only github.com public URLs are accepted — prevents SSRF to internal hosts.
_GITHUB_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$"
)


class IngestError(Exception):
    pass


def parse_github_url(url: str) -> tuple[str, str]:
    """Return (owner, repo) or raise IngestError."""
    m = _GITHUB_RE.match(url.strip())
    if not m:
        raise IngestError(f"Not a valid public GitHub URL: {url!r}")
    return m.group("owner"), m.group("repo")


def clone_repo(github_url: str) -> Path:
    """
    Shallow-clone (depth=1) a public GitHub repo into a fresh temp directory.

    Returns the path to the cloned repo root.
    The caller owns the lifecycle — clean up with shutil.rmtree(path.parent).
    """
    owner, repo = parse_github_url(github_url)
    clone_url = f"https://github.com/{owner}/{repo}.git"

    tmp = Path(tempfile.mkdtemp(prefix="codegraph_"))
    dest = tmp / repo
    try:
        result = subprocess.run(
            ["git", "clone", "--depth=1", "--quiet", clone_url, str(dest)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp, ignore_errors=True)
        raise IngestError("git clone timed out after 120 s")

    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise IngestError(
            f"git clone failed: {result.stderr.strip() or 'unknown error'}"
        )

    return dest
