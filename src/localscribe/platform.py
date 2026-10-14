"""Platform paths and small OS-specific helpers (v0.1: Linux + macOS)."""

from __future__ import annotations

import os
import platform as _p
import sys
from pathlib import Path


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    return sys.platform == "darwin"


def app_name() -> str:
    return "localscribe"


def data_dir() -> Path:
    if is_macos():
        base = Path.home() / "Library" / "Application Support" / "LocalScribe"
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) / "localscribe" if xdg else Path.home() / ".local" / "share" / "localscribe"
    base.mkdir(parents=True, exist_ok=True)
    return base


def model_dir() -> Path:
    d = data_dir() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def transcript_dir() -> Path:
    d = data_dir() / "transcripts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def spool_dir() -> Path:
    d = data_dir() / "spool"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cpu_arch() -> str:
    m = _p.machine().lower()
    if m in {"x86_64", "amd64"}:
        return "x86_64"
    if m in {"arm64", "aarch64"}:
        return "arm64"
    return m


def physical_cores() -> int:
    try:
        if is_linux():
            # Count unique core ids
            cores = set()
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("core id"):
                        cores.add(line.split(":", 1)[1].strip())
            if cores:
                return len(cores)
        if is_macos():
            import subprocess

            out = subprocess.check_output(["sysctl", "-n", "hw.physicalcpu"], text=True)
            return int(out.strip())
    except Exception:
        pass
    return os.cpu_count() or 1


def total_ram_bytes() -> int:
    try:
        if is_linux():
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) * 1024
        if is_macos():
            import subprocess

            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            return int(out.strip())
    except Exception:
        pass
    return 0
