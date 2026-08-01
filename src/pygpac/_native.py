"""
Isolated libgpac loading layer.

Per ADR-0001 (Decision 3), the way the native library is located and loaded
is kept in a single module so v1.1 can swap "look for a system copy" for
"look for a bundled copy next to the package first, then fall back to the
system" without touching the rest of the binding.

Library-search pattern (dll -> so -> dylib -> ctypes.util.find_library)
mirrors the official ctypes binding (gpac/gpac:
share/python/libgpac/libgpac.py) - not copied, same approach.
"""
import warnings
from ctypes import CDLL, c_char_p, c_int, cdll
from ctypes.util import find_library

# ABI version this binding was written and tested against.
# See ADR-0001 ("ABI drift mitigation" under Option A): GPAC exposes
# gf_gpac_abi_major()/gf_gpac_abi_minor() specifically so bindings can
# detect drift instead of silently reading a struct layout that changed.
# Bump these deliberately after re-verifying against a newer GPAC build.
EXPECTED_ABI_MAJOR = 16
EXPECTED_ABI_MINOR = 23


class GpacError(RuntimeError):
    """Raised when a libgpac call reports an error (GF_Err < 0)."""


def _load_libgpac() -> CDLL:
    errors = []
    for candidate in ("libgpac.dll", "libgpac.so", "libgpac.dylib"):
        try:
            return cdll.LoadLibrary(candidate)
        except OSError as e:
            errors.append(f"{candidate}: {e}")

    dll_path = find_library("gpac")
    if dll_path:
        try:
            return cdll.LoadLibrary(dll_path)
        except OSError as e:
            errors.append(f"{dll_path}: {e}")

    raise OSError(
        "Could not load libgpac (.so/.dll/.dylib). Make sure GPAC is "
        "installed and the library is on your system's library search "
        "path (see docs/dev-environment.md).\n" + "\n".join(errors)
    )


libgpac = _load_libgpac()

# Explicit argtypes/restype for every wrapped function - never rely on
# ctypes defaults (the default restype is c_int, which silently truncates
# a 64-bit pointer return value; see ADR-0001).
libgpac.gf_gpac_version.argtypes = []
libgpac.gf_gpac_version.restype = c_char_p

libgpac.gf_gpac_abi_major.argtypes = []
libgpac.gf_gpac_abi_major.restype = c_int

libgpac.gf_gpac_abi_minor.argtypes = []
libgpac.gf_gpac_abi_minor.restype = c_int

libgpac.gf_sys_init.argtypes = [c_int, c_char_p]
libgpac.gf_sys_init.restype = c_int

libgpac.gf_sys_close.argtypes = []
libgpac.gf_sys_close.restype = None

libgpac.gf_error_to_string.argtypes = [c_int]
libgpac.gf_error_to_string.restype = c_char_p


def error_to_string(err: int) -> str:
    return libgpac.gf_error_to_string(err).decode("utf-8")


def check_abi() -> bool:
    """Compare the loaded libgpac's ABI against the version this binding
    was written for. Returns True on match, warns and returns False on
    mismatch (does not raise - see ADR-0001 for the rationale: a
    minor/micro mismatch is often still safe, so this is left as a
    warning rather than a hard failure, matching the official binding's
    behavior)."""
    major = libgpac.gf_gpac_abi_major()
    minor = libgpac.gf_gpac_abi_minor()
    if (major, minor) != (EXPECTED_ABI_MAJOR, EXPECTED_ABI_MINOR):
        warnings.warn(
            f"pygpac was written for libgpac ABI "
            f"{EXPECTED_ABI_MAJOR}.{EXPECTED_ABI_MINOR}, but the loaded "
            f"libgpac reports ABI {major}.{minor}. Undefined behavior or "
            f"crashes are possible - see docs/dev-environment.md.",
            RuntimeWarning,
            stacklevel=2,
        )
        return False
    return True
