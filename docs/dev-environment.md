# Development environment setup (Linux)

This documents ADR-0001 (`docs/adr/0001-binding-technology.md`) WBS item #1: getting a working GPAC build and confirming the ctypes approach actually loads it.

## Prerequisites

- `git`, `gcc`/`g++`, `make`, `pkg-config`.
- `zlib1g-dev` at minimum. For the full list of optional third-party dependencies GPAC can pick up (codecs, X11, audio backends, etc.), see the [GPAC Build Guide for Linux](https://wiki.gpac.io/Build/build/GPAC-Build-Guide-for-Linux/). None of these are required for a v1-scoped build (filter session + built-in filters + properties) — GPAC's `configure` auto-detects what's present and disables what isn't, rather than failing.

## Building libgpac from source (recommended over the prebuilt nightly `.deb`)

```sh
git clone --depth 1 https://github.com/gpac/gpac.git gpac_src
cd gpac_src
./configure
make -j$(nproc)
```

This produces `bin/gcc/libgpac.so.<major>.<minor>.<micro>` (plus the `gpac` and `MP4Box` binaries), linked against whatever optional libraries are actually present on the build machine. Building from source, rather than using a prebuilt package, sidesteps the pitfall below.

## Known pitfall: the prebuilt nightly `.deb` targets Ubuntu 24.04

The `gpac_latest_head_linux64.deb` permalink published on gpac.io is built against Ubuntu 24.04 LTS and links against specific ffmpeg soname versions (e.g. `libavcodec.so.60`). On a different/newer distribution (verified on Ubuntu 26.04), those exact sonames aren't present (e.g. the system ships `libavcodec.so.62` instead), and loading fails outright — `ctypes.CDLL`/`dlopen` must resolve every `DT_NEEDED` entry at load time, so this isn't a lazy-symbol-resolution issue that can be worked around, and isn't specific to a bug in the packaging.

This is concrete evidence supporting Decision 3 in ADR-0001: libgpac's runtime dependency chain is genuinely OS/distribution-version sensitive, which is exactly why bundling (planned for v1.1) needs the dependency-matching work described there, rather than being a simple "copy the .so into the wheel" step.

## Verifying the setup: ctypes smoke test

`scripts/smoke_test.py` loads `libgpac` via ctypes and calls `gf_sys_init`/`gf_sys_close`, using the same library-search pattern as the official ctypes binding (`share/python/libgpac/libgpac.py`) and reporting the ABI-version functions identified in ADR-0001's "ABI drift mitigation" section.

Run it with the library on the search path, e.g.:

```sh
LD_LIBRARY_PATH=/path/to/gpac_src/bin/gcc python3 scripts/smoke_test.py
```

Confirmed working output (2026-08-01, GPAC master, ABI 16.23, built from source on Ubuntu 26.04):

```
Loaded: <CDLL 'libgpac.so', ...>
gf_gpac_version(): 26.08-DEV-revUNKNOWN-master
gf_gpac_abi_major/minor(): 16 23
gf_sys_init() -> 0 (0 == GF_OK)
gf_sys_close() OK - smoke test passed
```

## Running the package's test suite locally

Once `libgpac` is built (see above) and the package is installed (`pip install -e ".[dev]"`), point `LD_LIBRARY_PATH` at the built library and run pytest:

```sh
LD_LIBRARY_PATH=/path/to/gpac_src/bin/gcc pytest -v
```

### Notes specific to a WSL2 + Windows-mounted-repo setup

If the repository lives on the Windows filesystem and is accessed from WSL2 via `/mnt/c/...` (rather than natively inside the Linux filesystem), a few WSL2-specific quirks showed up during verification and are worth knowing about upfront:

- A minimal WSL2 base image may be missing `python3-venv` (`python3 -m venv` fails with "ensurepip is not available") and `pip` itself (`python3 -m pip` -> "No module named pip"). Bootstrapping `pip` via `python3 get-pip.py --user --break-system-packages` (see [get-pip.py](https://bootstrap.pypa.io/get-pip.py)) works without root and without a venv.
- Recent Debian/Ubuntu Python builds are "externally managed" (PEP 668) and refuse plain `pip install` outside a venv - `--break-system-packages` is required for a `--user` install if you don't want to set up a venv (which itself needs the missing `python3-venv` package, i.e. `sudo apt install python3-venv` first).
- pytest may warn that it can't create its cache directory under `/mnt/c/...` (`Operation not permitted`) - this is a Windows/WSL9P filesystem permission quirk, not a real test failure; safe to ignore, or work around by keeping a clone of the repo inside the native Linux filesystem instead of `/mnt/c/...`.

## Status

WBS items #1 and #2 (ADR-0001) are complete:

- environment set up, `libgpac` located and loaded, `gf_sys_init`/`gf_sys_close` round-trip verified via ctypes (item #1);
- package skeleton (`pyproject.toml`, `src/pygpac/` with an isolated `_native.py` loading layer and ABI guard, `tests/`, GitHub Actions CI) in place and verified end-to-end against a real built `libgpac` - `pytest` passes 3/3 (item #2).

Next: WBS item #3 - ctypes declarations for the filter session / filter / property functions, cross-checked against the official `libgpac.py` as a reference.
