"""Non-invasive host capability discovery for AMALGAMA."""
import platform
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Capabilities:
    os: str
    supported_readonly_prototype: bool
    native_event_sensor: str
    native_enforcement: str
    automatic_install: bool = False


def discover(system=None):
    system = system or platform.system()
    if system == "Darwin":
        return Capabilities("macOS", True, "FSEvents / Endpoint Security (not implemented)",
                            "System Extensions / OS policy (not implemented)")
    if system == "Linux":
        return Capabilities("Linux", True, "fanotify / audit / eBPF (not implemented)",
                            "LSM / systemd sandbox (not implemented)")
    if system == "Windows":
        return Capabilities("Windows", True, "ETW (not implemented)",
                            "App Control / Defender APIs (not implemented)")
    return Capabilities(system, False, "unknown", "unknown")


def report(system=None):
    return asdict(discover(system))
