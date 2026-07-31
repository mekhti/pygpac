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

## Status

WBS item #1 (ADR-0001) is complete: environment set up, `libgpac` located and loaded, `gf_sys_init`/`gf_sys_close` round-trip verified via ctypes.

Next: WBS item #2 - package skeleton (`pyproject.toml`, `pytest`, basic CI).
