"""Small UI-independent editable-design operations; no scientific run actions.

Edits validate a complete candidate before replacing the immutable model.
Selection is transient editor state and is never part of design identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from ohlab.target_design import TargetDesign2D
from ohlab.io.designs import design_from_json, save_design


def empty_design(ny: int = 64, nx: int = 64) -> TargetDesign2D:
    """Return a zero-background design in dimensionless centered pixel units."""
    return TargetDesign2D({
        "schema_version": 1, "rasterizer_version": "center_sample_overwrite_v1",
        "coordinate_system": "centered_pixels_y_down_v1",
        "canvas": {"ny": ny, "nx": nx}, "background_intensity": 0.0,
        "objects": [],
    })


@dataclass
class EditorState:
    """Editable document plus transient selection and explicit-save diagnostics."""

    design: TargetDesign2D = field(default_factory=empty_design)
    selected_id: str | None = None
    error: str | None = None
    saved_path: Path | None = None


def select_object(editor: EditorState, object_id: str | None) -> None:
    """Select a stable object ID without changing the document."""
    ids = {obj["id"] for obj in editor.design.to_dict()["objects"]}
    if object_id is not None and object_id not in ids:
        raise ValueError(f"selection: unknown object ID {object_id!r}")
    editor.selected_id = object_id


def replace_design(editor: EditorState, design: TargetDesign2D) -> None:
    """Atomically replace a fully validated document and coherent selection."""
    if not isinstance(design, TargetDesign2D):
        raise TypeError("design: expected TargetDesign2D")
    candidate = TargetDesign2D(design.to_dict())
    objects = candidate.to_dict()["objects"]
    editor.design = candidate
    editor.selected_id = objects[0]["id"] if objects else None
    editor.saved_path = None
    editor.error = None


def import_design(editor: EditorState, data: bytes) -> bool:
    """Import explicit JSON bytes; failure preserves document and selection."""
    try:
        candidate = design_from_json(data)
    except (TypeError, ValueError) as exc:
        editor.error = f"{type(exc).__name__}: {exc}"
        return False
    replace_design(editor, candidate)
    return True


def _commit(editor: EditorState, spec: dict) -> bool:
    try:
        candidate = TargetDesign2D(spec)
    except (TypeError, ValueError) as exc:
        editor.error = f"{type(exc).__name__}: {exc}"
        return False
    editor.design = candidate
    editor.error = None
    editor.saved_path = None
    return True


def update_canvas(editor: EditorState, ny: int, nx: int, background: float) -> bool:
    """Resize the centered window; preserve all existing object parameters."""
    spec = editor.design.to_dict()
    spec["canvas"] = {"ny": ny, "nx": nx}
    spec["background_intensity"] = background
    return _commit(editor, spec)


def add_object(editor: EditorState, kind: str) -> bool:
    """Add one supported object; sizes/positions are dimensionless pixels."""
    defaults = {
        "disk": {"cx_px": 0.0, "cy_px": 0.0, "radius_px": 8.0},
        "rectangle": {"cx_px": 0.0, "cy_px": 0.0, "width_px": 16.0, "height_px": 8.0},
        "segment": {"x0_px": -8.0, "y0_px": 0.0, "x1_px": 8.0, "y1_px": 0.0, "width_px": 2.0},
    }
    if kind not in defaults:
        editor.error = f"ValueError: unsupported object type {kind!r}"
        return False
    spec = editor.design.to_dict()
    identifier = uuid4().hex
    spec["objects"].append({"id": identifier, "type": kind,
                            "parameters": defaults[kind], "intensity": 0.5})
    if not _commit(editor, spec):
        return False
    editor.selected_id = identifier
    return True


def update_object(editor: EditorState, object_id: str,
                  parameters: Mapping[str, object], intensity: float) -> bool:
    """Validate an object edit before replacing any part of the document."""
    spec = editor.design.to_dict()
    for obj in spec["objects"]:
        if obj["id"] == object_id:
            obj["parameters"] = dict(parameters)
            obj["intensity"] = intensity
            return _commit(editor, spec)
    editor.error = f"ValueError: unknown object ID {object_id!r}"
    return False


def delete_object(editor: EditorState, object_id: str) -> bool:
    """Delete an explicitly selected object; choose a remaining object coherently."""
    spec = editor.design.to_dict()
    found = [obj for obj in spec["objects"] if obj["id"] == object_id]
    if not found:
        editor.error = f"ValueError: unknown object ID {object_id!r}"
        return False
    spec["objects"] = [obj for obj in spec["objects"] if obj["id"] != object_id]
    if not _commit(editor, spec):
        return False
    editor.selected_id = spec["objects"][0]["id"] if spec["objects"] else None
    return True


def move_object(editor: EditorState, object_id: str, offset: int) -> bool:
    """Move one layer by -1 or +1; later list entries overwrite earlier ones."""
    if type(offset) is not int or offset not in (-1, 1):
        raise ValueError("offset: expected -1 or +1")
    spec = editor.design.to_dict()
    ids = [obj["id"] for obj in spec["objects"]]
    if object_id not in ids:
        editor.error = f"ValueError: unknown object ID {object_id!r}"
        return False
    index = ids.index(object_id)
    destination = index + offset
    if not 0 <= destination < len(ids):
        return False
    spec["objects"][index], spec["objects"][destination] = spec["objects"][destination], spec["objects"][index]
    return _commit(editor, spec)


def save_copy(editor: EditorState, *, runs_root: Path) -> Path | None:
    """Explicitly save a new editable JSON copy; never derive a path from uploads."""
    path = runs_root / "designs" / f"{uuid4().hex}.json"
    try:
        # The public I/O function validates ancestors before creating its file.
        # Root creation is app-owned and no existing design is overwritten.
        from apps.workbench import _reject_link_ancestors

        _reject_link_ancestors(path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)
        result = save_design(path, design=editor.design)
    except (OSError, TypeError, ValueError) as exc:
        editor.error = f"{type(exc).__name__}: {exc}"
        return None
    editor.saved_path = result
    editor.error = None
    return result
