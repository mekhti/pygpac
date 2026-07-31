# ADR-0001: pygpac binding technology (choosing how to wrap libgpac)

**Status:** Accepted for v1; the v2+ scope (custom filters, bundling) remains subject to future ADRs
**Date:** 2026-08-01
**Deciders:** project owner

## Final decision

For pygpac v1 (filter session + built-in C filters + properties, ~1 month target, solo + Claude pairing), **ctypes** is used:

- a working reference implementation on this exact API (the official GPAC binding) reduces the risk and time spent guessing function signatures/struct layout;
- it requires no compiler and no cross-platform build matrix — the fastest path to the timeline goal (Decision 2);
- it defaults to dynamic linking only — it doesn't raise LGPL compliance questions as long as v1 relies on a system-installed GPAC (Decision 3);
- the main weakness of ctypes — no build-time type checking against the real headers — is mitigated in practice by GPAC's own runtime ABI-version API (see "ABI drift mitigation" under Option A).

Custom filters (`FilterCustom` equivalent, context item 2) and bundling libgpac into the wheel (Decision 3) are deliberately deferred past v1, but the v1 architecture must reserve extension points for them (see Decisions 1 and 3) so that adding them in v1.1/v2 doesn't require a change of binding technology or a breaking change to the public API.

## Context

pygpac is an independent Python binding for **libgpac** (the core of GPAC, written in C, LGPL-2.1-or-later). A technology needs to be chosen for generating/writing the binding: ctypes, cffi, Cython, pybind11, or SWIG.

Below are the characteristics of libgpac that actually matter for this choice (verified against the upstream headers, `include/gpac/`, master branch):

1. **The API is huge.** `include/gpac/` has ~60 public headers (`filters.h`, `isomedia.h`, `mpegts.h`, `dash.h`, `scenegraph*.h`, etc.). `filters.h` alone is 5348 lines with 77 top-level macros. Full coverage in v1 is unrealistic with any technology — the "auto-generate everything" appeal comes up less often in practice than it seems, because even with a generator, a sane public API still has to be curated by hand.

2. **Filters are a C vtable.** `GF_FilterRegister` is a struct of ~10 function pointers (`process`, `configure_pid`, `initialize`, `finalize`, `update_arg`, `process_event`, `reconfigure_output`, `probe_url`, `probe_data`, ...). Writing custom filters in Python (like `FilterCustom` in the official binding) requires not just calling C functions from Python, but marshaling C→Python callbacks — this is the hardest and most consequential part of the binding, and every tool handles it differently.

3. **`GF_PropertyValue` is a tagged union.** ~20 variants (int/int64, fractions (`GF_Fraction`), 2D/3D/4D vectors, strings, data blobs, lists of strings/numbers/vectors), selected by a `type` field. No tool resolves this automatically — a manual mapping table between `GF_PropType` and the union field is required regardless of tool.

4. **Memory management and object ownership** — GPAC's conventions (who frees a property, when it's copied vs. referenced) must be explicitly built into the binding, independent of the chosen tool.

5. **Multi-threaded scheduler.** The filter session can run in lock-free/lock/direct modes; in multi-threaded mode, C callbacks into a custom filter may arrive from a non-main thread — so callback GIL-safety matters regardless of the chosen tool.

6. **LGPL-2.1-or-later license.** Distributing wheels with a compiled libgpac baked in (via `auditwheel`/`delvewheel`) is treated, for LGPL compliance purposes, close to static linking — the project must either link dynamically and rely on a system-installed GPAC, or address source-availability/relink obligations when bundling. This is a separate question from the technology choice, but some tools (see below) nudge toward one default or the other.

### Important upstream precedent

- GPAC already has an official Python binding: `share/python/libgpac/libgpac.py`, hand-written in **ctypes**, documented upstream as "initial work" with incomplete coverage. This is the only one of the candidate technologies with a working example on this exact API.
- GPAC's roadmap lists **"Rust and SWIG Bindings"**. The community has already built a Rust binding (`gpac_rs`, https://github.com/geniussportsgroup/gpac_rs), and in a discussion (issue [gpac/gpac#2890](https://github.com/gpac/gpac/issues/2890)) GPAC maintainers indicated they're open to accepting third-party bindings under the same LGPL-2.1-or-later license. This means: (a) upstream is open to alternative bindings, but (b) if upstream ships an official SWIG binding, part of the value of a separate SWIG-based pygpac variant may disappear — worth checking status periodically.

## Scope decisions

### Decision 1 (2026-08-01): custom Python filters are out of scope for v1, but must be designed as an extension point

**User's framing:** custom filters aren't needed for v1, but the design must allow adding/fitting them in later versions.

**What this changes in the evaluation:**
- Marshaling C→Python callbacks (context item 2) stops being an implementation requirement for v1 — only an architectural one. This removes weight from the options where the callback mechanism is the most expensive part (the C++ shim for pybind11, directors for SWIG), since that cost can be deferred.
- v1 effectively reduces to filter-session orchestration: loading built-in C filters by name/config string, reading/writing properties, managing the session. This is a narrow, well-bounded API subset — closer to what the "dynamic" options (ctypes/cffi ABI) handle most simply and with the fewest dependencies.
- But the risk doesn't disappear — it shifts into an architectural requirement: the chosen option must allow adding a callback mechanism later *without* changing the binding technology overall. In practice this means:
  - Keeping all entry points into libgpac (session, filter, property loading) behind an internal layer/module, rather than spreading direct C API calls across the codebase — so a future `FilterCustom` equivalent can be added without rewriting the public API.
  - Building the object model from v1 onward with a split mirroring the official binding: `Filter` (a wrapper over a built-in C filter, outbound calls only) as a separate concept from a future `FilterCustom` (an object that C will call *back into*) — even if `FilterCustom` isn't implemented yet, its place in the API shouldn't require a breaking change later.
  - Not picking an implementation that physically rules out adding callbacks later (none of the five candidate options have this limitation — `CFUNCTYPE`/`ffi.callback`/`extern "Python"`/`cdef` functions/directors can all be added to an existing module without switching tools), so this constraint doesn't eliminate any technology option, but it does obligate a specific internal architecture from the start.

**Bottom line:** the callback problem remains a differentiator for the future (v2+), but stops being a blocker for v1 — the project can move forward with whichever option is best for orchestrating built-in filters, provided the architectural constraint above is respected.

### Decision 2 (2026-08-01): priority is shipping v1 fast, target ~1 month

**User's framing:** ideally the first version should ship as fast as possible, target within a month.

**Further clarified (see "v1 timeline estimate" section):**
- Resourcing: solo + Claude as a pair (no dedicated team).
- v1 scope confirmed as minimal: filter session + built-in C filters + properties (no direct per-packet/PID access at the v1 level, no custom filters — see Decision 1).

**What this changes in the evaluation:**
- The "speed" priority clearly outweighs resilience to GPAC ABI drift for v1. This makes the "dynamic" cluster (ctypes / cffi ABI) the practical default for v1: no cross-platform build matrix, no compiler, the shortest path from "decision" to "working code."
- Within the dynamic cluster, **ctypes is now preferable to cffi-ABI specifically for speed**: ctypes has a working reference implementation on this exact API (the official GPAC binding) — the risk and time spent "guessing" function signatures and struct/union layout is lower than with cffi, where no such direct example exists. cffi's cleaner syntax doesn't pay for that gap given a "ship in a month" goal.
- This effectively resolves Question 3 (readiness for a cross-platform build) for v1 — choosing ctypes/cffi-ABI simply doesn't need a build matrix, regardless of the answer to that question. Question 3 stays relevant only for a future move to a compiled option (v2+, if/when callback support via a compiled tool is needed).
- Question 4 (LGPL packaging stance) isn't resolved by this alone: even with ctypes, the project still needs to decide whether v1 relies on a GPAC the user has pre-installed (`pip install pygpac` + a separate "install GPAC" instruction) or attempts to vendor something. For the "ship in a month" goal, **relying on a system-installed/separately-installed GPAC is the fastest path** (no need to solve bundling and LGPL compliance right now), but this still needs an explicit user decision, not just a conclusion drawn from the speed priority.

### Decision 3 (2026-08-01): v1 relies on system GPAC, bundling libgpac into the wheel is a v1.1 task

**Context:** the user ultimately prefers bundling libgpac into the wheel (more convenient for end users — `pip install` without a separate GPAC install). The question raised was why this isn't trivially automated via GitHub Actions.

**Why bundling isn't "just set up CI" (recorded here for the future v1.1 implementation):**
1. `libgpac` itself has to come from somewhere for each platform — either built from source (its own build process, with optional third-party dependencies auto-detected on the build machine), or extracted from GPAC's official builds. The latter is faster, but still needs an extraction script and verification per OS.
2. Not just the `libgpac` file needs bundling — the whole chain of its transitive dependencies does too.
3. **A key constraint specific to the ctypes option (verified, not assumed):** the standard tools for baking dependencies into a wheel — `auditwheel` (Linux), `delvewheel` (Windows), `delocate` (macOS) — work by analyzing the import table of a **compiled extension** (`.so`/`.pyd`/`.dylib` belonging to the package itself). Dependencies loaded at runtime via `ctypes.CDLL`/`dlopen` (which is exactly how v1 works) are **not detected automatically** by these tools — what to vendor has to be specified by hand (`delvewheel --add-dll` and equivalents), and the library search path (RPATH/`install_name`/DLL search path) has to be fixed up manually so `ctypes.CDLL` finds the bundled copy rather than a system one (or nothing at all).
4. LGPL obligations when bundling a binary: pin the exact GPAC version/commit, provide access to the corresponding source, include the LICENSE — mechanically simple, but requires a deliberate checklist (not something Claude should decide unilaterally — the legal side needs separate confirmation).
5. Testing has to happen in an environment without a system GPAC — otherwise it's easy to get a falsely-green CI run (the build machine happened to already have a system copy).
6. Not a one-time cost: every GPAC version bump means rebuilding/re-extracting for every platform again.

This adds roughly **+7–14 working days** to the v1 WBS (fast path: reusing GPAC's official builds rather than building GPAC from source) — moving the "likely" scenario from ~19–23 to ~26–37 days, which is already tight against the "~1 month" goal (Decision 2).

**Decision:** the "~1 month" goal (Decision 2) takes priority. v1 requires a GPAC pre-installed by the user (`pip install pygpac` + documented separate GPAC installation, e.g. via `gpac.io/downloads` or a system package manager); bundling libgpac into the wheel is planned work for **v1.1**, done once the core binding (session/filters/properties) is already working and verified.

**Consequence for v1 architecture:** the library-loading mechanism (`ctypes.CDLL(...)`) must be isolated in one place (e.g. a dedicated `_native.py` module resolving the path to `libgpac`), not spread across the codebase — so that v1.1 can swap "look in the system" for "look for a bundled copy next to the package first, then fall back to the system" without rewriting the rest of the binding.

## v1 timeline estimate: methodology and calculation

The question "how do you estimate the timeline" breaks into two independent parts: **(1) how to decompose and estimate the scope of work** and **(2) how to convert that scope into a calendar deadline given the available resourcing**. Both follow.

### 1. Decomposition methodology

1. Break the scope into short, independently verifiable deliverables (a WBS) — each one should end in something that can actually be run and observed, not an abstract "percent done" on a feature.
2. Give each deliverable a **three-point estimate** (optimistic / likely / pessimistic) instead of a single number — especially where there's no direct reference code to copy the pattern from.
3. Explicitly flag which deliverables are **precedented** (there's a working example in the official ctypes GPAC binding that can be used as a behavioral reference — without copying code) — uncertainty is lower there. And which are **unprecedented** (e.g. field-by-field validation of `GF_PropertyValue` handling across real property types) — uncertainty is higher there and needs a bigger buffer.
4. Add a separate line item for "integration and debugging against real GPAC" — in binding projects this is consistently the most underestimated part (struct layout mismatches, GPAC version differences on the developer's machine, differences between builds), and it can't be folded into the estimates of individual modules.
5. Sum the pessimistic estimates separately from the likely ones — if the pessimistic scenario already doesn't fit in a month, that's a signal to cut scope up front, not after the deadline is blown.

### 2. WBS for the v1 scope (session + built-in filters + properties, ctypes)

| # | Deliverable | Precedented? | Optimistic | Likely | Pessimistic |
|---|---|---|---|---|---|
| 1 | Environment: build/install GPAC locally, confirm the location of `libgpac.so`/`.dll`/`.dylib`, a minimal `gf_init`/`gf_close` smoke test via ctypes | Partially (ready-made GPAC builds exist, but no ready-made Python code) | 1 day | 2 days | 4 days |
| 2 | Package skeleton: `pyproject.toml`, layout, pytest, basic CI (one Linux runner) | Yes (standard Python boilerplate — this is where Claude pairing helps the most) | 0.5 day | 1 day | 2 days |
| 3 | ctypes declarations: enums, constants, signatures (`argtypes`/`restype`) for filter session/filter/property functions, cross-checked against the official `libgpac.py` as a reference | Yes | 2 days | 3 days | 5 days |
| 4 | `FilterSession` wrapper: create/run/stop, blocking/non-blocking, `load_src`/`load_dst`/`load`, basic graph linking | Yes (direct analog in the reference) | 2 days | 3 days | 5 days |
| 5 | `Filter` wrapper + properties: marshaling `GF_PropertyValue` (the tagged union, see the context section) across the main types (int/string/fraction/list) | Partially — the union-handling logic itself isn't precedented in code (not copied), but its behavior is | 3 days | 5 days | 8 days |
| 6 | Integration tests against real built-in filters (e.g. a simple source → sink graph on a test file), debugging discrepancies | No — this is the "first contact with reality" | 2 days | 4 days | 7 days |
| 7 | Minimal documentation for PyPI readability (README examples), publishing a test release (TestPyPI or a GitHub release) | Yes | 0.5 day | 1 day | 2 days |
| 8 | Buffer for the unexpected (GPAC versions, the developer's Windows/Linux environment, review) | — | — | +20% | +30% |
| | **Total (working days)** | | **~11** | **~19–23** | **~33–39** |

The buffer is already accounted for as a separate line and roughly folded into the "likely"/"pessimistic" ranges (rounded up).

### 3. Converting to a calendar deadline

The key missing parameter is **how many hours per week are actually available**, not just "who's writing the code." Roughly (assuming 1 working day ≈ 6 focus-hours):

| Pace | Focus-days/week (equivalent) | ~19 working days (likely scenario) | ~35 working days (pessimistic) |
|---|---|---|---|
| Full-time (~5 focus-days/wk) | 5 | ~4 weeks | ~7 weeks |
| Part-time evenings/weekends (~2 focus-days/wk) | 2 | ~9.5 weeks | ~17.5 weeks |

**Conclusion:** the "1 month" goal is realistic for the likely scenario **only at a pace close to full-time**. At a part-time pace, a month covers, at best, the optimistic scenario (~11 days ≈ 5–6 weeks part-time — also already past a month). This isn't a reason to abandon the goal, but a signal: if weekly capacity is limited, either cut scope further (e.g. defer item 6, "integration tests across several filters," down to a couple of scenarios instead of broad coverage), or accept a ~6–8 week timeline up front instead of 4.

### Where Claude pairing actually speeds things up, and where it doesn't

- **Speeds things up noticeably:** package boilerplate (item 2), writing ctypes declarations against the reference and cross-checking them (item 3), test and documentation drafts (item 7).
- **Speeds things up little or not at all:** installing/building GPAC and verifying the developer's environment (item 1 — bottlenecked by the actual machine and its quirks), debugging discrepancies against GPAC's real behavior on actual media files (items 5–6 — bottlenecked by the need to actually run the code and look at the result; this still requires human time for the "run it → see the bug → fix it" iteration loop).
- Practical takeaway: bank the AI-pairing speedup mainly in items 2, 3, 7 (which is already reflected above via a narrower estimate range), but don't expect it to compress items 1, 5, 6.

## Options considered

### Option A: ctypes (stdlib)

| Criterion | Assessment |
|---|---|
| Implementation complexity | Medium (all marshaling done by hand) |
| Compiler required for the user | No |
| LGPL compliance by default | Good (always dlopen, dynamic linking only) |
| Callback support (custom filters) | Via `ctypes.CFUNCTYPE`, by hand |
| Build-time type checking | No — mismatches against GPAC's structs only surface at runtime; see mitigation below |
| Precedent on this exact API | Yes — the official GPAC binding is written this way |

**Pros:**
- Part of the standard library — neither the developer nor the end user needs a compiler or extra dependencies; can be distributed as a pure Python package.
- Always dynamically loads the `.so`/`.dll` at runtime — naturally satisfies the LGPL dynamic-linking requirement; the question of "what's baked into the wheel" doesn't arise at all.
- There's a working, live example solving the same problems (tagged union, custom-filter callbacks, filter-session handling) in the official binding — usable as a reference (without copying code).

**Cons:**
- The slowest call overhead among the options (not critical for managing the filter session — the heavy lifting still happens in C, Python only orchestrates — but could become noticeable with frequent calls, e.g. per-packet work).
- Structs/unions are described by hand in Python and have to be manually kept in sync as GPAC updates — there's no compilation against the real headers, so ABI mismatches only surface at runtime (a segfault or corrupted memory). See "ABI drift mitigation" below for how this is managed in practice.
- Python exceptions inside a C callback can't "bubble up" naturally — they have to be caught/logged manually (the same issue applies to cffi ABI mode).
- `ctypesgen` (auto-generating a binding from headers) exists, but handles complex macros poorly and isn't actively maintained — in practice it doesn't eliminate manual work for this API.

**ABI drift mitigation (why the "no build-time check" con is manageable in practice):**

The lack of build-time verification splits into two distinct risks that need different fixes:

1. *Initial transcription error* — getting a struct field's type wrong, or forgetting to set `restype` on a function that returns a pointer (a classic, well-documented ctypes pitfall: the default `restype` is `c_int`, which silently truncates a 64-bit pointer on a 64-bit system). Note that a compiled option (cffi API mode, Cython) only actually catches this *if* the build directly `#include`s the real GPAC headers (`set_source()` in cffi, `cdef extern from "gpac/filters.h"` in Cython) rather than a hand-curated declaration subset — which in turn requires GPAC's dev headers on the build machine, reintroducing some of the build complexity Decisions 2–3 were meant to avoid. If declarations are hand-curated either way (the realistic case for any tool here, given the macro-heavy headers), the compiled option mostly checks "are my own declarations self-consistent," not "do they match real GPAC" — so the gap versus ctypes is smaller than the comparison table alone suggests.
2. *ABI drift between GPAC versions* — code written correctly today, a future GPAC release changes a struct. GPAC ships a purpose-built API for exactly this in `include/gpac/version.h`:
   ```c
   u32 gf_gpac_abi_major();
   u32 gf_gpac_abi_minor();
   u32 gf_gpac_abi_micro();
   ```
   with a maintainer comment right next to it: *"WARNING: when bumping, reflect the changes in share/python/libgpac.py!!"* — confirming upstream is aware their own ctypes binding is ABI-sensitive and expects bindings to check this programmatically.

**Practical mitigation for v1 (compatible with staying on ctypes/cffi-ABI):**
- Pin v1 to a specific GPAC version/ABI it was built and tested against.
- In the library-loading module (`_native.py`, already an isolated extension point per Decision 3), call `gf_gpac_abi_major/minor/micro()` at import time and compare against the expected values — fail loudly with a clear error on mismatch, instead of silently continuing with a possibly-wrong struct layout.
- Add a CI job that periodically pulls a fresh GPAC nightly and runs the test suite — this won't protect an individual end user at install time, but it surfaces drift within roughly a day instead of via a user's crash report.
- Set `restype`/`argtypes` explicitly for every wrapped function (never rely on ctypes defaults), with extra test coverage specifically for `GF_PropertyValue` and any pointer-returning function.

### Option B: cffi

Two modes: **ABI** (like ctypes, dlopen at runtime) and **API** (compiles a C stub at build time).

| Criterion | Assessment |
|---|---|
| Implementation complexity | Medium |
| Compiler required for the user | No (ABI) / Yes at build time (API, but not necessarily for the end user if prebuilt wheels are published) |
| LGPL compliance by default | Good in ABI mode; in API mode depends on how the C stub is built |
| Callback support | ABI: same as ctypes; API: the recommended `extern "Python"` mechanism — faster and cleaner than raw callback pointers |
| Build-time type checking | Yes in API mode, for the generated stub |
| Precedent on this exact API | No direct one, but the `extern "Python"` pattern fits `GF_FilterRegister` well |

**Pros:**
- A cleaner API than ctypes, at comparable simplicity.
- In API mode, `extern "Python"` is the officially recommended callback mechanism instead of raw pointers — a direct, documented answer to the custom-filter problem (context item 2).
- `cdef()` can parse a (cleaned-up/preprocessed) subset of headers — not fully automatic for GPAC (macros like `GF_EXPORT` get in the way), but closer to it than ctypes.
- Good PyPy support, should that ever become a requirement.

**Cons:**
- API mode needs a compiler at build time (not necessarily for the end user if prebuilt wheels are published, but it adds a CI matrix).
- GPAC's headers are heavily macro-laden — `cdef()` will need a hand-curated declaration subset regardless, not a raw include of the real headers.
- Fewer examples specifically for large multimedia C APIs than Cython/pybind11.

### Option C: Cython

| Criterion | Assessment |
|---|---|
| Implementation complexity | Medium-high (requires learning Cython syntax) |
| Compiler required for the user | No (given a wheel), yes when building from source |
| LGPL compliance by default | Requires an explicit decision (see below) |
| Callback support | Via `cdef` functions assigned directly into the vtable struct |
| Build-time type checking | Yes — compiled against real declarations |
| Precedent on this exact API | None, but a strong general precedent exists: lxml (wrapping libxml2/libxslt) |

**Pros:**
- A well-understood way to wrap large/complex C APIs at the Python-object level; lxml is a direct precedent (a deliberate choice to hand-write rather than generate, for an API of comparable complexity).
- `cdef` functions map naturally onto `GF_FilterRegister` callback roles, with normal Python exception propagation at the boundary.
- Compiled once into a C extension — no per-call libffi overhead; mismatches against GPAC's structs are caught at compile time rather than at runtime.
- The developer writes Python-like code, not a separate language (unlike pybind11/SWIG).

**Cons:**
- Requires learning Cython syntax (`.pyx`/`.pxd`) — a real barrier to entry for contributors.
- Needs a cross-platform build matrix (Windows/macOS/Linux × Python versions), e.g. via `cibuildwheel`.
- Like any compiled extension, can end up statically baking in libgpac by default unless the build is deliberately set up otherwise — the LGPL packaging question has to be handled consciously, not by default.

### Option D: pybind11

| Criterion | Assessment |
|---|---|
| Implementation complexity | High for a C library (needs a C++ shim) |
| Compiler required for the user | No (given a wheel), yes at build time |
| LGPL compliance by default | Requires an explicit decision |
| Callback support | Excellent — but only after the API is wrapped in C++ |
| Build-time type checking | Yes |
| Precedent on this exact API | None |

**Pros:**
- Very mature callback support via `std::function` — if libgpac were already a C++ library, this would be one of the strongest options.
- Excellent documentation and a large community (for C++ projects).

**Cons:**
- libgpac is plain C, and pybind11 is designed around C++ (classes, templates, RAII). Using pybind11 as intended would first require writing a separate C++ shim over `GF_FilterRegister`, the tagged union, and so on, and only then wrapping that shim with pybind11 — effectively double work (C→C++, then C++→Python).
- Adds a second "native" language to the project (C++) alongside Python, with no clear necessity if the only goal is wrapping a C API.
- The same build matrix as Cython, without Cython's "write it almost like Python" ergonomics.

### Option E: SWIG

| Criterion | Assessment |
|---|---|
| Implementation complexity | Medium-high, with caveats |
| Compiler required for the user | No (given a wheel), yes at build time |
| LGPL compliance by default | Requires an explicit decision |
| Callback support | Via the "directors" feature — specifically built for this scenario |
| Build-time type checking | Yes |
| Precedent on this exact API | Upstream itself lists SWIG in its roadmap (see context) |

**Pros:**
- Can generate the wrapper from a (cleaned) description of C declarations — potentially less hand-written glue when trying to expand API coverage over time.
- The "directors" feature exists specifically so a scripting-language (Python) object can override/implement C function pointers — a direct match for the custom-filter problem (context item 2).
- Multi-language support "for free": if Python-only ever stops being the whole scope, SWIG already targets many languages from one `.i` file (though pygpac's current scope is Python-only).
- GPAC already mentions SWIG in its own roadmap — choosing SWIG creates a chance of approach compatibility with a possible future official binding.

**Cons:**
- Both SWIG's own documentation and outside reviews describe working with directors/callback pointers as one of the trickiest corners of the tool; the community notes that many tutorials are outdated and that SWIG is "too flexible and not optimized for any one thing."
- The tagged union `GF_PropertyValue` and the capability-negotiation structures would still need hand-written typemaps — "auto-generate everything" doesn't hold for this particular part of the API.
- The same per-platform build matrix as Cython/pybind11.
- If upstream ships an official SWIG binding (a roadmap item), it would directly compete with/overlap an independent SWIG-based pygpac — worth re-evaluating this option once the official one's status is known.

## Trade-off analysis

The options naturally split into two clusters:

**"Dynamic" (ctypes, cffi ABI)** — no compiler required, distributed as a pure Python package, always dynamically linked (LGPL — fine by default), a working reference exists on this exact API (the official ctypes binding). Cost: ABI mismatches between GPAC versions only surface at runtime, not at build time; callback and exception marshaling is entirely manual (see the ABI drift mitigation under Option A for how this risk is managed in practice).

**"Compiled" (cffi API, Cython, pybind11, SWIG)** — types are checked at build time against real declarations, which reduces the risk of silently drifting from GPAC's ABI; but they need a cross-platform build matrix (`cibuildwheel`-style) and a deliberate LGPL packaging decision (not the default, as with ctypes).

**Custom-filter callback marshaling** remains the main long-term differentiator between the options (see Decision 1), but **isn't a requirement for v1** as long as the architecture reserves a place for it. For v1 (orchestrating built-in C filters), the weight shifts toward simplicity and minimal dependencies: ctypes/cffi-ABI solve exactly this problem with the least overhead (no compiler, no build matrix), while the compiled options (Cython/pybind11/SWIG/cffi-API) mostly earn their added complexity through compile-time type checking and future callback support — i.e. their advantage is mostly about v2+, not v1. The tagged union `GF_PropertyValue`, as before, is **not** a differentiator — a manual mapping table is needed regardless, at any v1 scope.

Given that real API coverage in v1 will in any case be limited to the core entities (filter session, filters, PIDs, packets, properties — matching the official binding), the "generate the wrapper from headers" advantage of SWIG/cffi matters less in practice here than it would for a simpler, more uniform API.

## Consequences (regardless of the final choice)

- An explicit, separately maintained mapping table between `GF_PropType` and the `GF_PropertyValue.value` union field will be needed — no tool resolves this automatically.
- An explicit GIL-safety and exception-handling strategy is needed at the C→Python callback boundary (relevant under any multi-threaded filter-session mode).
- An explicit LGPL packaging decision is needed: dynamic linking against a system/vendored-but-separately-shipped libgpac, or bundling with source-availability/relink obligations addressed — the legal side isn't for Claude to decide alone; it goes to the user (see CLAUDE.md).
- v1's API coverage should be deliberately scoped (session/filters/PIDs/packets/properties), regardless of how "automated" the chosen tool is.
- v1's public API must reserve a place for a future `FilterCustom` equivalent (see Decision 1): a separate concept of "wrapper over a built-in filter" vs. a future "object implementing a filter in Python," without implementing the latter immediately.

## Recommendation for the next step

Since callback marshaling is out of scope for v1 (Decision 1), the thing worth prototyping isn't "the riskiest part" but the v1 scope itself: wrap `gf_init` + loading/linking a few built-in filters + reading/writing properties on 1–2 candidates from the "dynamic" cluster (ctypes and cffi-ABI) — this gives a signal on the real effort of the v1 scope specifically. A prototype with a custom filter and a callback remains useful, but becomes a v2-planning task rather than a blocker on today's technology choice.

## Open questions for the user to decide

All questions raised in the first version of this document are resolved:

1. ~~Are custom Python filters (`FilterCustom` equivalent) needed in the MVP~~ — **resolved** (Decision 1, 2026-08-01): not needed in v1, but must be designed as an extension point.
2. ~~Priority: shipping speed for the first version, or resilience to GPAC ABI drift~~ — **resolved** (Decision 2, 2026-08-01): priority is speed, target ~1 month (at a full-time pace; see "v1 timeline estimate"). Practically settles the choice in favor of ctypes for v1.
3. ~~Readiness to support a cross-platform extension build~~ — **moot** (2026-08-01): not relevant for v1 (ctypes needs no build matrix). Remains an open question only for future v2+ planning (a compiled option for the sake of callbacks).
4. ~~LGPL packaging stance: system GPAC or bundling~~ — **resolved** (Decision 3, 2026-08-01): v1 relies on a pre-installed system GPAC; bundling libgpac into the wheel is a separate v1.1 task, estimated at ~7–14 extra working days. The legal side of the bundling itself (LGPL obligations when distributing a binary) still needs separate confirmation when v1.1 is being prepared — not something Claude decides alone.

Technology for v1 (session + built-in filters + properties): **ctypes**, with explicit architectural isolation of the library-loading layer (see Decision 3) and of the `GF_PropertyValue` marshaling/callback extension point (see Decision 1), so the move to bundling and to custom filters in later versions is painless.

## Sources

- GPAC repo and roadmap: https://github.com/gpac/gpac
- `include/gpac/filters.h` (master branch, `GF_FilterRegister`, `GF_PropertyValue`): https://github.com/gpac/gpac/blob/master/include/gpac/filters.h
- `include/gpac/version.h` (master branch, `gf_gpac_abi_major/minor/micro`): https://github.com/gpac/gpac/blob/master/include/gpac/version.h
- Official Python binding (reference, not to be copied): https://github.com/gpac/gpac/blob/master/share/python/libgpac/libgpac.py
- Python API documentation: https://doxygen.gpac.io/group__pyapi__grp.html
- Discussion of the Rust binding and maintainers' stance on third-party binding licensing: https://github.com/gpac/gpac/issues/2890
- Community Rust binding (precedent for a third-party binding): https://github.com/geniussportsgroup/gpac_rs
- cffi: ABI/API modes, `extern "Python"`: https://cffi.readthedocs.io/
- SWIG: directors and callbacks: https://swig.org/Doc4.0/SWIG.html
- Cython vs. pybind11 vs. cffi comparison (Stefan Behnel, Cython core developer): http://blog.behnel.de/posts/cython-pybind11-cffi-which-tool-to-choose.html
- LGPL and distribution via wheel bundling (general context, not legal advice): https://github.com/opencv/opencv-python/issues/615
