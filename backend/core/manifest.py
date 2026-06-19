"""
M1 — Detect the tech stack of a cloned repo and decide which analyzers to run.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# ─── Detection tables ─────────────────────────────────────────────────────────

_JS_FRAMEWORKS: dict[str, str] = {
    "next": "next",
    "react": "react",
    "react-dom": "react",
    "@remix-run/react": "remix",
    "nuxt": "nuxt",
    "vue": "vue",
    "svelte": "svelte",
}

_JS_DB_LAYERS: dict[str, str] = {
    "@prisma/client": "prisma",
    "prisma": "prisma",
    "drizzle-orm": "drizzle",
    "@supabase/supabase-js": "supabase",
    "knex": "knex",
    "pg": "pg",
    "mysql2": "mysql2",
    "better-sqlite3": "sqlite",
    "mongoose": "mongoose",
}

_PY_FRAMEWORKS: dict[str, str] = {
    "django": "django",
    "fastapi": "fastapi",
    "flask": "flask",
    "starlette": "starlette",
    "litestar": "litestar",
}

_PY_DB_LAYERS: dict[str, str] = {
    "sqlalchemy": "sqlalchemy",
    "alembic": "sqlalchemy",   # alembic implies sqlalchemy
    "django": "django_orm",    # django implies its ORM
    "tortoise-orm": "tortoise",
    "peewee": "peewee",
    "databases": "databases",
}

# ─── Output type ──────────────────────────────────────────────────────────────


@dataclass
class StackManifest:
    repo_url: str
    local_path: str
    detected_frameworks: list[str] = field(default_factory=list)
    db_layers: list[str] = field(default_factory=list)
    run_python_analyzer: bool = False
    run_js_analyzer: bool = False


# ─── Public API ───────────────────────────────────────────────────────────────


def detect_stack(local_path: Path, repo_url: str = "") -> StackManifest:
    manifest = StackManifest(repo_url=repo_url, local_path=str(local_path))

    _check_js(local_path, manifest)
    _check_python(local_path, manifest)

    # Deduplicate while preserving first-seen order
    manifest.detected_frameworks = _dedup(manifest.detected_frameworks)
    manifest.db_layers = _dedup(manifest.db_layers)

    return manifest


# ─── JS / TS detection ────────────────────────────────────────────────────────


def _check_js(root: Path, manifest: StackManifest) -> None:
    pkg_path = root / "package.json"
    if not pkg_path.exists():
        return

    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    all_deps: dict[str, str] = {}
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        all_deps.update(pkg.get(section) or {})

    for dep, label in _JS_FRAMEWORKS.items():
        if dep in all_deps:
            manifest.detected_frameworks.append(label)

    for dep, label in _JS_DB_LAYERS.items():
        if dep in all_deps:
            manifest.db_layers.append(label)

    # Prisma schema file is a stronger signal than package.json alone
    if (root / "prisma" / "schema.prisma").exists():
        manifest.db_layers.append("prisma")

    manifest.run_js_analyzer = True


# ─── Python detection ─────────────────────────────────────────────────────────


def _check_python(root: Path, manifest: StackManifest) -> None:
    deps: set[str] = set()

    req = root / "requirements.txt"
    if req.exists():
        _parse_requirements(req, deps)

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        _parse_pyproject(pyproject, deps)

    # setup.cfg fallback
    setup_cfg = root / "setup.cfg"
    if setup_cfg.exists():
        _parse_setup_cfg(setup_cfg, deps)

    if not deps:
        return

    for key, label in _PY_FRAMEWORKS.items():
        if key in deps:
            manifest.detected_frameworks.append(label)

    for key, label in _PY_DB_LAYERS.items():
        if key in deps:
            manifest.db_layers.append(label)

    manifest.run_python_analyzer = True


def _parse_requirements(path: Path, deps: set[str]) -> None:
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip().lower()
            if not line or line.startswith(("#", "-", ".")):
                continue
            name = re.split(r"[>=<!~\[\s;@]", line)[0].strip()
            if name:
                deps.add(name)
    except OSError:
        pass


def _parse_pyproject(path: Path, deps: set[str]) -> None:
    try:
        import tomllib  # stdlib in Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]  # pip install tomli on <3.11
        except ImportError:
            return

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return

    raw_deps: list[str] = []
    # PEP 621
    raw_deps += data.get("project", {}).get("dependencies", [])
    raw_deps += data.get("project", {}).get("optional-dependencies", {}).values()
    # Poetry
    raw_deps += list(data.get("tool", {}).get("poetry", {}).get("dependencies", {}).keys())
    raw_deps += list(data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {}).keys())
    # build-system
    raw_deps += data.get("build-system", {}).get("requires", [])

    for item in raw_deps:
        if isinstance(item, str):
            name = re.split(r"[>=<!~\[\s;@]", item.lower())[0].strip()
            if name and name != "python":
                deps.add(name)
        elif isinstance(item, dict):
            # handles lists of dicts (some poetry formats)
            pass


def _parse_setup_cfg(path: Path, deps: set[str]) -> None:
    try:
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(path, encoding="utf-8")
        raw = cfg.get("options", "install_requires", fallback="")
        for line in raw.splitlines():
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[>=<!~\[\s;@]", line)[0].strip()
            if name:
                deps.add(name)
    except Exception:
        pass


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _dedup(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
