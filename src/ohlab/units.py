"""SI unit multipliers.

The numerical core of :mod:`ohlab` stores, passes, and returns **SI base units
only** (see ``docs/math_conventions.md`` section 2). This module provides
multipliers so that call sites can be written readably without ever storing a
non-SI value::

    wavelength_m = 633 * NM      # -> 6.33e-07 metres
    pitch_m      = 3.74 * UM     # -> 3.74e-06 metres

Deliberately, this module contains **multipliers only** and no conversion
functions. A function such as ``to_micrometres(x)`` would invite a non-SI
quantity to be stored or passed onward, which the conventions forbid.

All constants are exact ``float`` values in SI base units.
"""

from __future__ import annotations

import math

__all__ = ["NM", "UM", "MM", "CM", "DEG"]

#: Nanometre expressed in metres. ``633 * NM`` is a red HeNe wavelength.
NM: float = 1e-9

#: Micrometre expressed in metres. Typical SLM pixel pitches are a few ``UM``.
UM: float = 1e-6

#: Millimetre expressed in metres.
MM: float = 1e-3

#: Centimetre expressed in metres.
CM: float = 1e-2

#: Degree expressed in radians. ``45 * DEG`` is ``math.pi / 4``.
DEG: float = math.pi / 180.0
