"""
Minimal ctypes smoke test for libgpac (ADR-0001, v1 WBS item #1).

Mirrors the library-loading pattern used by the official ctypes binding
(gpac/gpac: share/python/libgpac/libgpac.py) - not copied, just the same
approach: try libgpac.dll, then libgpac.so, then libgpac.dylib, fall back
to ctypes.util.find_library, then call gf_sys_init/gf_sys_close and report
the GPAC version and ABI numbers (see the "ABI drift mitigation" section
of docs/adr/0001-binding-technology.md).

Usage:
    LD_LIBRARY_PATH=/path/to/gpac/bin/gcc python3 scripts/smoke_test.py
"""
import sys
from ctypes import cdll, c_int, c_char_p
from ctypes.util import find_library


def load_libgpac():
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
    raise OSError("Could not load libgpac:\n" + "\n".join(errors))


def main():
    libgpac = load_libgpac()
    print("Loaded:", libgpac)

    libgpac.gf_gpac_version.restype = c_char_p
    libgpac.gf_gpac_abi_major.restype = c_int
    libgpac.gf_gpac_abi_minor.restype = c_int
    libgpac.gf_sys_init.argtypes = [c_int, c_char_p]
    libgpac.gf_error_to_string.argtypes = [c_int]
    libgpac.gf_error_to_string.restype = c_char_p

    print("gf_gpac_version():", libgpac.gf_gpac_version().decode("utf-8"))
    print(
        "gf_gpac_abi_major/minor():",
        libgpac.gf_gpac_abi_major(),
        libgpac.gf_gpac_abi_minor(),
    )

    err = libgpac.gf_sys_init(0, None)
    print("gf_sys_init() ->", err, "(0 == GF_OK)")
    if err < 0:
        print("gf_error_to_string:", libgpac.gf_error_to_string(err).decode("utf-8"))
        sys.exit(1)

    libgpac.gf_sys_close()
    print("gf_sys_close() OK - smoke test passed")


if __name__ == "__main__":
    main()
