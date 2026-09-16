"""Strict PNG decoding at the optional image-I/O boundary.

The fixed PNG header is inspected before reading the remaining encoded bytes.
Pillow then verifies and decodes separate in-memory streams of that same
snapshot. This separates genuine filesystem OSErrors from decoder OSErrors
without a blanket exception handler or a general PNG parser.
"""

from __future__ import annotations

from contextlib import closing
from io import BytesIO
import os
import struct
from typing import Any
import zlib

import numpy as np
import numpy.typing as npt

from ..grid import SamplingGrid
from ..targets import grayscale8_to_intensity

__all__ = ["load_target_intensity"]

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _validate_header(header: bytes, grid: SamplingGrid, path: str) -> None:
    """Check only the fixed signature/IHDR layout and the supported contract."""
    if len(header) != 33 or header[:8] != _PNG_SIGNATURE:
        raise ValueError(f"{path!r}: expected a PNG signature and complete IHDR")
    if header[8:12] != b"\x00\x00\x00\x0d" or header[12:16] != b"IHDR":
        raise ValueError(f"{path!r}: expected a 13-byte IHDR as the first PNG chunk")
    width, height = struct.unpack(">II", header[16:24])
    if (height, width) != grid.shape:
        raise ValueError(
            f"{path!r}: declared PNG shape {(height, width)} does not match "
            f"grid.shape {grid.shape}; expected (ny, nx), with no resizing"
        )
    bit_depth, color_type = header[24:26]
    if bit_depth != 8 or color_type != 0:
        raise ValueError(
            f"{path!r}: expected source bit depth 8 and grayscale color type 0; "
            f"got bit depth {bit_depth}, color type {color_type}"
        )


def _validate_decoded_metadata(image: Any, grid: SamplingGrid) -> None:
    """Use public Pillow metadata; decoded L alone cannot establish bit depth."""
    if image.format != "PNG" or image.mode != "L":
        raise ValueError(
            f"expected PNG decoded mode L; got format {image.format!r}, "
            f"mode {image.mode!r}"
        )
    # Documented APNG MIME identification also catches n_frames == 1, where
    # is_animated is false. No private Pillow chunk/decoder fields are used.
    if image.get_format_mimetype() == "image/apng" or image.n_frames != 1:
        raise ValueError("APNG is unsupported, including single-frame APNG")
    if "transparency" in image.info:
        raise ValueError("grayscale transparency is unsupported")
    if image.size != (grid.nx, grid.ny):
        raise ValueError(
            f"decoded PNG shape {(image.height, image.width)} does not match "
            f"grid.shape {grid.shape}"
        )


def load_target_intensity(
    path: str | os.PathLike[str], *, grid: SamplingGrid
) -> npt.NDArray[np.float64]:
    """Load a static 8-bit grayscale PNG as target intensity in a.u., [0, 1].

    Actual PNG content is required regardless of filename extension. The
    source must have bit depth 8, color type 0, decoded mode L, no transparency
    and no APNG animation metadata (even a one-frame animation is rejected).
    Declared dimensions must match grid before full pixel decoding; decoded
    shape is checked again. Pixel [i, j] maps directly to grid.x[j], grid.y[i].

    Return grayscale / 255 as a fresh, writable, C-contiguous native float64
    array of shape (ny, nx). An all-zero image is valid and remains zero.
    No resizing, orientation correction, gamma/profile conversion, clipping,
    thresholding, contrast stretching, peak or power normalization is applied.
    Metadata never changes grid pitch, raster ordering, or code values.
    This is design intensity, not calibrated radiometry or a known phase.

    TypeError reports wrong path/grid types. ValueError reports unsupported
    encodings or identified format/decoder failures, with path and stage;
    decoder causes are chained. Filesystem OSError subclasses are preserved.
    Missing Pillow raises ImportError only on use. Pillow's existing size,
    malformed/truncated-data protections and global settings are retained.

    The source file, image objects and memory streams are closed on success
    or failure. Encoded bytes are buffered after the header check; this is not
    a streaming loader or an exhaustive validator for every malformed PNG.
    """
    if not isinstance(grid, SamplingGrid):
        raise TypeError(f"grid must be SamplingGrid, got {type(grid).__name__}")
    if not isinstance(path, (str, os.PathLike)):
        raise TypeError(f"path must be str or PathLike[str], got {type(path).__name__}")
    filename = os.fspath(path)
    if not isinstance(filename, str):
        raise TypeError("path must resolve to str, not bytes")

    # Keep all real filesystem operations outside decoder error translation.
    # The header is read and checked before the remaining encoded data is read.
    with open(filename, "rb") as source:
        header = source.read(33)
        _validate_header(header, grid, filename)
        encoded = header + source.read()

    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        if exc.name == "PIL":
            raise ImportError(
                "PNG loading requires Pillow from the optional ohlab[images] "
                "extra; no dependency is installed automatically"
            ) from exc
        raise

    stage = "PNG integrity verification"
    try:
        with BytesIO(encoded) as stream, closing(Image.open(stream, formats=["PNG"])) as image:
            _validate_decoded_metadata(image, grid)
            image.verify()

        # Pillow documents reopening after verify(): it does not decode pixels.
        stage = "PNG pixel decoding"
        with BytesIO(encoded) as stream, closing(Image.open(stream, formats=["PNG"])) as image:
            _validate_decoded_metadata(image, grid)
            image.load()
            _validate_decoded_metadata(image, grid)
            grayscale = np.array(image, copy=True)
    except (OSError, SyntaxError, ValueError, EOFError, struct.error, zlib.error) as exc:
        # These operations read BytesIO only: OSError here is a decoder error,
        # never an open/read/permission error from the user's filesystem.
        raise ValueError(f"{filename!r}: {stage} failed: {exc}") from exc

    if grayscale.shape != grid.shape:
        raise ValueError(
            f"{filename!r}: decoded array shape {grayscale.shape} does not match "
            f"grid.shape {grid.shape}"
        )
    return grayscale8_to_intensity(grayscale, grid=grid)
