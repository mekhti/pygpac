# Contributing to pygpac

Thanks for your interest in contributing to pygpac, an independent Python binding for [libgpac](https://github.com/gpac/gpac).

## Project status

This project is in early bootstrap. Expect the API surface, packaging, and build tooling to change without notice until a first tagged release.

## Before you start

- Check open issues/discussions for the intended architecture before submitting large changes — the binding strategy (ctypes / cffi / Cython / pybind11 / SWIG / header-based codegen) is not finalized yet.
- Get familiar with libgpac's C API via https://doxygen.gpac.io and the filter session model described at https://wiki.gpac.io/Filters/Filters.
- Don't copy code from the official ctypes binding shipped in `gpac/gpac` (`share/python/libgpac/libgpac.py`) without checking license/attribution — this project aims for an independent implementation.

## Development workflow

1. Fork the repository and branch from `main`.
2. Keep commits focused, with descriptive messages in the imperative mood (e.g. "Add FilterSession wrapper").
3. Add or update tests for any behavioral change.
4. Run the test suite and linters before opening a PR (exact commands will be documented here once build tooling is set up).
5. Open a PR against `main` describing the change, its motivation, and any dependency on a specific GPAC/libgpac version.

## Code style

Python code should follow PEP 8. Type hints are encouraged. A linter/formatter config will be added as the project matures.

## Reporting issues

Use GitHub Issues. Include your GPAC/libgpac version (`gpac -version`), OS, and Python version.

## License

By contributing, you agree that your contributions will be licensed under the project's LGPL-2.1-or-later license (see [LICENSE](LICENSE)).
