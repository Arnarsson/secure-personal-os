#!/usr/bin/env python3
"""
Cross-platform configuration helpers for Secure Personal OS.

Provides standard locations for data, logs, screenshots, security vault,
and the permissions configuration file. Honors environment overrides.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional


APP_ENV_PREFIX = "PERSONAL_OS"


def _is_windows() -> bool:
    return os.name == "nt"


def repo_root() -> Path:
    """Best-effort repository root (dev checkout)."""
    here = Path(__file__).resolve()
    # personal_os/config.py -> repo root is parent of package dir
    return here.parent.parent


def home_dir() -> Path:
    return Path.home()


def base_dir() -> Path:
    """Base application data directory (overridable via PERSONAL_OS_HOME)."""
    override = os.getenv(f"{APP_ENV_PREFIX}_HOME")
    if override:
        return Path(override).expanduser()

    if sys.platform == "darwin":
        return home_dir() / "Library" / "Application Support" / "SecurePersonalOS"
    if _is_windows():
        appdata = os.getenv("APPDATA") or (home_dir() / "AppData" / "Roaming")
        return Path(appdata) / "SecurePersonalOS"
    # Linux/Unix
    xdg = os.getenv("XDG_DATA_HOME")
    base = Path(xdg) if xdg else (home_dir() / ".local" / "share")
    return base / "secure_personal_os"


def config_dir() -> Path:
    xdg = os.getenv("XDG_CONFIG_HOME")
    if sys.platform == "darwin":
        return home_dir() / "Library" / "Application Support" / "SecurePersonalOS" / "config"
    if _is_windows():
        appdata = os.getenv("APPDATA") or (home_dir() / "AppData" / "Roaming")
        return Path(appdata) / "SecurePersonalOS" / "config"
    base = Path(xdg) if xdg else (home_dir() / ".config")
    return base / "secure_personal_os"


def logs_dir() -> Path:
    return base_dir() / "logs"


def screenshots_dir() -> Path:
    return logs_dir() / "screenshots"


def security_dir() -> Path:
    return base_dir() / "security"


def vault_path() -> Path:
    override = os.getenv(f"{APP_ENV_PREFIX}_VAULT")
    return Path(override).expanduser() if override else (security_dir() / "credential_vault.enc")


def audit_log_path() -> Path:
    override = os.getenv(f"{APP_ENV_PREFIX}_AUDIT_LOG")
    return Path(override).expanduser() if override else (logs_dir() / "audit.log")


def permissions_path() -> Path:
    """Resolve the permissions.yaml path with sensible defaults.

    Priority:
    1) PERSONAL_OS_PERMISSIONS env
    2) repo-local permissions/permissions.yaml (dev)
    3) config_dir/permissions.yaml
    """
    override = os.getenv(f"{APP_ENV_PREFIX}_PERMISSIONS")
    if override:
        return Path(override).expanduser()
    repo_candidate = repo_root() / "permissions" / "permissions.yaml"
    if repo_candidate.exists():
        return repo_candidate
    return config_dir() / "permissions.yaml"


def ensure_dirs() -> None:
    for d in [base_dir(), config_dir(), logs_dir(), screenshots_dir(), security_dir()]:
        d.mkdir(parents=True, exist_ok=True)


def substitutions() -> Dict[str, str]:
    """Common substitution variables for configs and templates."""
    tmpdir = os.getenv("TMPDIR") or (str(Path(os.getenv("TEMP", "/tmp"))))
    return {
        "APP_HOME": str(base_dir()),
        "CONFIG_DIR": str(config_dir()),
        "LOGS_DIR": str(logs_dir()),
        "SCREENSHOTS_DIR": str(screenshots_dir()),
        "SECURITY_DIR": str(security_dir()),
        "VAULT_FILE": str(vault_path()),
        "AUDIT_LOG": str(audit_log_path()),
        "REPO_ROOT": str(repo_root()),
        "HOME": str(home_dir()),
        "TMPDIR": tmpdir,
        "CWD": str(Path.cwd()),
    }


def expand_placeholders(value: str) -> str:
    """Expand env vars, ~, and ${VAR} placeholders from substitutions()."""
    if not isinstance(value, str):
        return value
    # First expand ~ and $ENV style
    expanded = os.path.expanduser(os.path.expandvars(value))
    # Then custom ${VAR} tokens
    mapping = substitutions()
    for key, repl in mapping.items():
        expanded = expanded.replace(f"${{{key}}}", repl)
    return expanded


def expand_in_config(cfg: Dict) -> Dict:
    """Recursively expand placeholders in a dict-based configuration."""
    def _expand(obj):
        if isinstance(obj, dict):
            return {k: _expand(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_expand(x) for x in obj]
        if isinstance(obj, str):
            return expand_placeholders(obj)
        return obj

    return _expand(cfg)

