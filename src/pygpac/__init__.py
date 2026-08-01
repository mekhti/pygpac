"""
pygpac - independent Python bindings for libgpac (GPAC multimedia framework).

v1 scope (see docs/adr/0001-binding-technology.md): filter session
orchestration over built-in C filters and properties. Custom Python
filters and library bundling are deliberately out of scope for v1 - see
the ADR for the extension points reserved for them.
"""
from . import _native
from ._native import GpacError, check_abi, error_to_string

__version__ = "0.1.0"

_initialized = False


def init(mem_track: int = 0, profile: str | None = None) -> None:
    """Initialize libgpac. Safe to call more than once - subsequent calls
    are no-ops. See gf_sys_init() in the GPAC documentation for the
    meaning of mem_track/profile."""
    global _initialized
    if _initialized:
        return
    check_abi()
    profile_bytes = profile.encode("utf-8") if profile is not None else None
    err = _native.libgpac.gf_sys_init(mem_track, profile_bytes)
    if err < 0:
        raise GpacError(f"gf_sys_init failed: {error_to_string(err)}")
    _initialized = True


def close() -> None:
    """Shut down libgpac. Make sure any libgpac resources (filter
    sessions, etc.) have been destroyed first."""
    global _initialized
    if not _initialized:
        return
    _native.libgpac.gf_sys_close()
    _initialized = False


def version() -> str:
    """Return the loaded libgpac's version string (e.g.
    '26.08-DEV-revUNKNOWN-master')."""
    return _native.libgpac.gf_gpac_version().decode("utf-8")


def abi_version() -> tuple[int, int]:
    """Return the loaded libgpac's (ABI major, ABI minor)."""
    return (_native.libgpac.gf_gpac_abi_major(), _native.libgpac.gf_gpac_abi_minor())


__all__ = [
    "GpacError",
    "abi_version",
    "close",
    "init",
    "version",
]
