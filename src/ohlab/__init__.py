"""Open Holographic Lab (``ohlab``).

A reproducible computer-generated holography (CGH) simulator.

This package is currently at the scaffolding stage. It intentionally exposes
nothing beyond :data:`__version__`; the numerical core (units, validation,
:class:`SamplingGrid`, :class:`ComplexField`) is added in Milestone 0.

Normative references
--------------------
``docs/math_conventions.md``
    Units, sign conventions, array layout, coordinate and frequency grid
    definitions, FFT normalization. Code must match that document.
``docs/milestones.md``
    Milestone scope, status, and recorded limitations.

Notes
-----
This module must remain import-cheap and dependency-free. It must not import
NumPy, SciPy, or any submodule at package-import time, because ``setuptools``
resolves the project version from ``__version__`` here during the build.
"""

from __future__ import annotations

__all__ = ["__version__"]

#: Package version. This is the single source of truth for the version string;
#: ``pyproject.toml`` reads it via ``[tool.setuptools.dynamic]``.
__version__: str = "0.1.0.dev0"
