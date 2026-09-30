"""Bounded standalone editable-design JSON, separate from M5 run bundles."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile

from ..target_design import TargetDesign2D

__all__ = ["design_to_json", "design_from_json", "save_design", "load_design"]

_MAX_JSON_BYTES = 256 * 1024
_PARTIAL = ".ohlab-design-partial-"


def design_to_json(design: TargetDesign2D) -> bytes:
    """Export canonical UTF-8 JSON: sorted keys, indent=2, LF/final newline.

    The design schema/rasterizer versions, object order and finite scalar bits
    are retained. No raster or PNG quantization is involved. Export is bounded
    to 256 KiB and has no filesystem side effects.
    """
    if not isinstance(design, TargetDesign2D):
        raise TypeError("design: expected TargetDesign2D")
    encoded = (json.dumps(design.to_dict(), sort_keys=True, ensure_ascii=False,
                          allow_nan=False, indent=2) + "\n").encode("utf-8")
    if len(encoded) > _MAX_JSON_BYTES:
        raise ValueError(f"design JSON exceeds {_MAX_JSON_BYTES} encoded bytes")
    return encoded


def design_from_json(data: bytes) -> TargetDesign2D:
    """Validate at most 256 KiB of strict UTF-8 JSON before returning a model.

    Reject duplicate keys, nonstandard constants, unsupported fields/versions
    and invalid scalar domains. Input bytes are never retained as mutable data.
    A UTF-8 BOM is not part of this JSON format. Schema type errors remain
    TypeError; malformed encoding/syntax and invalid values raise ValueError.
    """
    if type(data) is not bytes:
        raise TypeError("design JSON: expected bytes")
    if len(data) > _MAX_JSON_BYTES:
        raise ValueError(f"design JSON exceeds {_MAX_JSON_BYTES} encoded bytes")

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"design JSON: duplicate key {key!r}")
            result[key] = value
        return result

    def constant(value: str) -> object:
        raise ValueError(f"design JSON: nonstandard constant {value!r}")

    try:
        text = data.decode("utf-8")
        specification = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"design JSON: invalid UTF-8 or JSON: {exc}") from exc
    return TargetDesign2D(specification)


def _path(value: str | os.PathLike[str]) -> Path:
    if not isinstance(value, (str, os.PathLike)) or not isinstance(os.fspath(value), str):
        raise TypeError("design path: expected str or PathLike[str]")
    path = Path(value).absolute()
    if path.name.startswith(_PARTIAL):
        raise ValueError("design path: reserved partial filename is not a completed design")
    return path


def _no_links(path: Path) -> None:
    for ancestor in (*reversed(path.parents), path):
        if not os.path.lexists(ancestor):
            continue
        info = ancestor.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError(f"{ancestor}: design paths do not support links or reparse points")


def load_design(path: str | os.PathLike[str]) -> TargetDesign2D:
    """Load a regular standalone design file with a bounded read, without mutation."""
    source = _path(path)
    _no_links(source)
    info = source.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{source}: expected a regular design file")
    if info.st_size > _MAX_JSON_BYTES:
        raise ValueError(f"design JSON exceeds {_MAX_JSON_BYTES} encoded bytes")
    with source.open("rb") as stream:
        data = stream.read(_MAX_JSON_BYTES + 1)
    return design_from_json(data)


def save_design(path: str | os.PathLike[str], *, design: TargetDesign2D) -> Path:
    """Publish a new design JSON file; never intentionally replace a destination.

    Parent must exist. Use an exclusively owned temporary sibling, write/fsync/
    close it, recheck absence, then rename. Windows rename refuses a destination
    appearing during publication. No retry, overwrite, migration, directory
    creation or unrelated cleanup occurs. Concurrent hostile filesystem changes,
    concurrent POSIX writers and power-loss durability are outside this bounded
    local-file contract. A failed write removes only the owned partial file;
    if cleanup fails, preserve the original exception and report its path.
    """
    encoded = design_to_json(design)
    destination = _path(path)
    _no_links(destination)
    if os.path.lexists(destination):
        raise FileExistsError(f"design destination already exists: {destination}")
    if not stat.S_ISDIR(destination.parent.lstat().st_mode):
        raise ValueError("design destination parent: expected a directory")
    descriptor, temporary = tempfile.mkstemp(prefix=_PARTIAL, suffix=".json", dir=destination.parent)
    stage = Path(temporary)
    try:
        try:
            stream = os.fdopen(descriptor, "wb")
        except BaseException:
            os.close(descriptor)
            raise
        with stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if os.path.lexists(destination):
            raise FileExistsError(f"design destination appeared during save: {destination}")
        os.rename(stage, destination)
    except BaseException as exc:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass
        except OSError as cleanup:
            exc.add_note(f"design cleanup failed; owned partial remains at {stage}: {cleanup}")
        raise
    return destination
