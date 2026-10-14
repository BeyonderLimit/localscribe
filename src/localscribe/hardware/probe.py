"""Capability probe (v0.1: CPU + RAM, no GPU)."""

from __future__ import annotations

import platform as _stdlib_platform
from dataclasses import asdict, dataclass

from ..platform import cpu_arch, physical_cores, total_ram_bytes


@dataclass
class HardwareProfile:
    os: str
    arch: str
    physical_cores: int
    ram_bytes: int
    cpu_features: list[str]
    battery_state: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _cpu_features() -> list[str]:
    features: list[str] = []
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("flags"):
                    flags = line.split(":", 1)[1].split()
                    wanted = {"avx", "avx2", "avx512f", "neon"}
                    features = sorted(wanted & set(flags))
                    break
    except Exception:
        pass
    return features


def probe() -> HardwareProfile:
    system = _stdlib_platform.system().lower()
    os_name = "macos" if system == "darwin" else "linux"
    return HardwareProfile(
        os=os_name,
        arch=cpu_arch(),
        physical_cores=physical_cores(),
        ram_bytes=total_ram_bytes(),
        cpu_features=_cpu_features(),
    )
