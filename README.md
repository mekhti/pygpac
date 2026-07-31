# pygpac

Independent Python bindings for [libgpac](https://github.com/gpac/gpac), the core library of the [GPAC](https://gpac.io) multimedia framework.

## Status

Early stage / work in progress. This repository currently contains only project scaffolding — no binding code yet. API, packaging, and build tooling are all subject to change.

## Why an alternative binding?

GPAC already ships an official `ctypes`-based Python binding (`libgpac.py`, under `share/python/libgpac/` in the [gpac/gpac](https://github.com/gpac/gpac) repo), which the upstream project itself describes as an initial effort covering filter sessions, filters, PIDs, packets, and custom filters. pygpac is a separate, independent implementation — the specific goals and technical approach (API coverage, packaging strategy, binding technology) are still being defined.

## About GPAC / libgpac

GPAC is an open-source multimedia framework (written in C, LGPL-2.1-or-later) for processing, inspecting, packaging, streaming, and playing back audio/video/subtitle content — MP4/ISOBMFF, MPEG-DASH, HLS, CENC encryption, and more. Its core is built around a filter-graph engine: filter sessions, filters, PIDs, and packets.

- Upstream: https://github.com/gpac/gpac
- Wiki: https://wiki.gpac.io
- C/Python/JS API reference: https://doxygen.gpac.io

## Installation

Not yet published to PyPI. Installation instructions will be added once the binding is buildable and packaged.

## License

LGPL-2.1-or-later — see [LICENSE](LICENSE), matching the license of libgpac itself.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
