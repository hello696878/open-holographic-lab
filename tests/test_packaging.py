"""Smoke tests for the packaging and test toolchain.

These tests contain no physics. They exist so that the packaging
configuration, the editable install, and the pytest configuration are all
verified end to end *before* any numerical code is written.

Without them, ``pytest`` on an empty suite exits with code 5 ("no tests
collected"), which is indistinguishable from a broken configuration.
"""

from __future__ import annotations

import sys


def test_package_is_importable() -> None:
    """The installed ``ohlab`` package can be imported.

    This proves that the ``src/`` layout, the setuptools package discovery
    configuration, and the editable install all agree.
    """
    import ohlab

    assert ohlab is not None


def test_version_is_a_nonempty_string() -> None:
    """``ohlab.__version__`` is a non-empty string.

    ``pyproject.toml`` resolves the distribution version from this attribute
    via ``[tool.setuptools.dynamic]``, so a non-string or empty value would
    break the build rather than merely being cosmetic.
    """
    import ohlab

    assert isinstance(ohlab.__version__, str)
    assert ohlab.__version__ != ""


def test_running_on_python_311_or_newer() -> None:
    """The interpreter satisfies the project's ``requires-python``.

    The project targets Python 3.11 (see CLAUDE.md). This guards against a
    test run accidentally executed by a different interpreter than the one in
    ``.venv``.
    """
    assert sys.version_info >= (3, 11)
