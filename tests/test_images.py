"""PNG boundary contracts; fixtures contain independently chosen sample bytes.

The small chunk writer only constructs fixtures (no production parsing).
It is needed because Pillow L-mode saves would miss the 2/4-bit source trap.
"""

from __future__ import annotations

import builtins
from io import BytesIO
from pathlib import Path
import struct
import subprocess
import sys
import zlib

import numpy as np
from PIL import Image, ImageFile, PngImagePlugin
import pytest

from ohlab.grid import SamplingGrid
from ohlab.io import images
from ohlab.io.images import load_target_intensity
from ohlab.targets import intensity_to_amplitude


def _grid(ny: int = 2, nx: int = 3) -> SamplingGrid:
    return SamplingGrid(ny=ny, nx=nx, dy=5e-6, dx=3.74e-6)


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload)) + kind + payload
        + struct.pack(">I", zlib.crc32(kind + payload))
    )


def _png(
    *, width: int = 3, height: int = 2, bits: int = 8,
    scanlines: bytes = b"\x00\x00\x33\x80\x00\xff\x66\xcc",
    extras: tuple[tuple[bytes, bytes], ...] = (),
    idat: bytes | None = None,
) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, bits, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header)
        + b"".join(_chunk(kind, value) for kind, value in extras)
        + _chunk(b"IDAT", zlib.compress(scanlines) if idat is None else idat)
        + _chunk(b"IEND", b"")
    )


@pytest.fixture
def png_path(tmp_path: Path) -> Path:
    path = tmp_path / "known.png"
    path.write_bytes(_png())
    return path


def test_image_known_pixels_intensity_and_amplitude(png_path: Path) -> None:
    # Literal rational values, not another target function, define intensity.
    expected = np.array([[0.0, 0.2, 128.0 / 255.0], [1.0, 0.4, 0.8]])
    intensity = load_target_intensity(png_path, grid=_grid())
    np.testing.assert_allclose(intensity, expected, rtol=2e-15, atol=0.0)
    amplitude = intensity_to_amplitude(intensity, grid=_grid())
    np.testing.assert_allclose(amplitude**2, expected, rtol=5e-15, atol=0.0)
    # Independently calculated with 80-digit Decimal.sqrt, not NumPy sqrt.
    np.testing.assert_allclose(amplitude[0, 2], 0.7084919084320762,
                               rtol=2e-15, atol=0.0)
    assert intensity.dtype == np.dtype(np.float64)
    assert intensity.dtype.isnative
    assert intensity.flags.owndata and intensity.flags.c_contiguous
    assert intensity.flags.writeable


def test_image_all_256_code_values(tmp_path: Path) -> None:
    scanlines = b"".join(b"\x00" + bytes(range(row * 16, row * 16 + 16))
                         for row in range(16))
    path = tmp_path / "all_codes.png"
    path.write_bytes(_png(width=16, height=16, scanlines=scanlines))
    actual = load_target_intensity(path, grid=_grid(16, 16))
    expected = np.array([n / 255.0 for n in range(256)]).reshape(16, 16)
    np.testing.assert_allclose(actual, expected, rtol=2e-15, atol=0.0)
    assert actual[0, 0] == 0.0 and actual[-1, -1] == 1.0
    assert actual[0, 1] > 0.0


@pytest.mark.parametrize("shape", [(2, 3), (3, 4), (4, 3), (3, 3)])
def test_image_orientation_grid_and_source_unchanged(tmp_path: Path, shape) -> None:
    ny, nx = shape
    rows = [bytes(10 + i * nx + j for j in range(nx)) for i in range(ny)]
    content = _png(width=nx, height=ny,
                   scanlines=b"".join(b"\x00" + row for row in rows))
    path = tmp_path / "orientation.png"
    path.write_bytes(content)
    grid = _grid(ny, nx)
    original_grid = grid.to_dict()
    first = load_target_intensity(path, grid=grid)
    second = load_target_intensity(path, grid=grid)
    expected = np.array([[float(v) / 255 for v in row] for row in rows])
    np.testing.assert_allclose(first, expected, rtol=2e-15, atol=0.0)
    assert first.shape == shape
    assert first.tobytes() == second.tobytes()  # exact deterministic output
    assert grid.to_dict() == original_grid
    assert path.read_bytes() == content
    assert not np.shares_memory(first, second)
    first[:] = 0.0
    np.testing.assert_allclose(second, expected, rtol=2e-15, atol=0.0)


def test_image_brightness_not_normalized_per_image(tmp_path: Path) -> None:
    results = []
    for peak in (64, 128):
        path = tmp_path / f"peak_{peak}.png"
        path.write_bytes(_png(scanlines=bytes([0, 32, peak, 0, 0, 0, 0, 0])))
        results.append(load_target_intensity(path, grid=_grid()))
    # Same stored 32 is exactly the same target value under both image maxima.
    assert results[0][0, 0] == results[1][0, 0]
    np.testing.assert_allclose(
        [results[0][0, 1], results[1][0, 1]], [64 / 255, 128 / 255],
        rtol=2e-15, atol=0.0,
    )


def test_image_blank_is_valid_zero(tmp_path: Path) -> None:
    path = tmp_path / "blank.png"
    path.write_bytes(_png(scanlines=b"\x00" * 8))
    intensity = load_target_intensity(path, grid=_grid())
    amplitude = intensity_to_amplitude(intensity, grid=_grid())
    assert np.all(intensity == 0.0) and np.all(amplitude == 0.0)


def test_image_metadata_does_not_transform_raster_or_grid(tmp_path: Path) -> None:
    pixels = np.array([[0, 51, 128], [255, 102, 204]], dtype=np.uint8)
    plain = tmp_path / "plain.png"
    tagged = tmp_path / "tagged.png"
    srgb_tagged = tmp_path / "srgb.png"
    Image.fromarray(pixels).save(plain)
    metadata = PngImagePlugin.PngInfo()
    metadata.add(b"gAMA", struct.pack(">I", 45455))
    metadata.add(b"sRGB", b"\x00")
    exif = Image.Exif()
    exif[274] = 6  # rotation tag must not rotate stored rows/columns
    Image.fromarray(pixels).save(
        tagged, pnginfo=metadata, exif=exif, dpi=(123, 234),
        icc_profile=b"metadata only; no colour management requested",
    )
    # Pillow omits sRGB when an ICC profile is supplied. Exercise it in a
    # separate file and assert metadata presence before claiming coverage.
    Image.fromarray(pixels).save(srgb_tagged, pnginfo=metadata)
    with Image.open(tagged) as decoded:
        assert {"gamma", "dpi", "icc_profile", "exif"} <= decoded.info.keys()
        assert decoded.getexif()[274] == 6
        assert decoded.info["icc_profile"] == b"metadata only; no colour management requested"
    with Image.open(srgb_tagged) as decoded:
        assert decoded.info["srgb"] == 0 and "gamma" in decoded.info
    grid = _grid()
    before = grid.to_dict()
    a = load_target_intensity(plain, grid=grid)
    b = load_target_intensity(tagged, grid=grid)
    c = load_target_intensity(srgb_tagged, grid=grid)
    assert a.tobytes() == b.tobytes() == c.tobytes()
    assert grid.to_dict() == before


def test_image_content_not_suffix(png_path: Path) -> None:
    path = png_path.with_suffix(".not_png")
    png_path.rename(path)
    assert load_target_intensity(path, grid=_grid()).shape == (2, 3)


@pytest.mark.parametrize("bits,packed", [(1, b"\x40"), (2, b"\x1b"), (4, b"\x05\xaf")])
def test_image_rejects_low_bit_source_even_when_decoded_as_l(
    tmp_path: Path, bits: int, packed: bytes
) -> None:
    path = tmp_path / f"gray{bits}.png"
    path.write_bytes(_png(width=4, height=1, bits=bits, scanlines=b"\x00" + packed))
    with Image.open(path) as decoded:
        decoded.load()
        assert decoded.mode == ("1" if bits == 1 else "L")
    with pytest.raises(ValueError, match="bit depth 8"):
        load_target_intensity(path, grid=_grid(1, 4))


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "LA", "P", "I;16"])
def test_image_rejects_unsupported_png_modes(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "unsupported.png"
    Image.new(mode, (3, 2)).save(path, format="PNG")
    with pytest.raises(ValueError, match="bit depth 8 and grayscale color type 0"):
        load_target_intensity(path, grid=_grid())


@pytest.mark.parametrize("mode", ["L", "F"])
def test_image_rejects_non_png_even_with_png_suffix(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "disguised.png"
    Image.new(mode, (3, 2)).save(path, format="TIFF")
    with pytest.raises(ValueError, match="PNG signature"):
        load_target_intensity(path, grid=_grid())


def test_image_rejects_grayscale_transparency(tmp_path: Path) -> None:
    path = tmp_path / "transparent.png"
    path.write_bytes(_png(extras=((b"tRNS", struct.pack(">H", 128)),)))
    with Image.open(path) as image:
        assert image.mode == "L" and image.info["transparency"] == 128
    with pytest.raises(ValueError, match="transparency"):
        load_target_intensity(path, grid=_grid())


def test_image_rejects_valid_single_frame_apng(tmp_path: Path) -> None:
    path = tmp_path / "single_frame.png"
    animation = (
        (b"acTL", struct.pack(">II", 1, 0)),
        (b"fcTL", struct.pack(">IIIIIHHBB", 0, 3, 2, 0, 0, 1, 10, 0, 0)),
    )
    path.write_bytes(_png(extras=animation))
    with Image.open(path) as image:
        assert image.n_frames == 1 and image.is_animated is False
        assert image.get_format_mimetype() == "image/apng"
        image.verify()
    with Image.open(path) as image:
        image.load()  # fixture is decodable, not merely a rejected corrupt file
    with pytest.raises(ValueError, match="APNG"):
        load_target_intensity(path, grid=_grid())


def test_image_rejects_multiframe_apng(tmp_path: Path) -> None:
    path = tmp_path / "multiple_frames.png"
    Image.new("L", (3, 2), 64).save(
        path, save_all=True, append_images=[Image.new("L", (3, 2), 128)],
        duration=100, loop=0,
    )
    with Image.open(path) as image:
        assert image.n_frames == 2 and image.is_animated
    with pytest.raises(ValueError, match="APNG"):
        load_target_intensity(path, grid=_grid())


def test_image_declared_dimensions_rejected_before_reading_payload_or_decoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HeaderOnly(BytesIO):
        def read(self, size=-1):
            assert size == 33, "payload must not be read on dimension mismatch"
            return super().read(size)
    source = HeaderOnly(_png(width=1_000_000, height=1))
    monkeypatch.setattr(images, "open", lambda *args: source, raising=False)
    def forbidden_decode(*args, **kwargs):
        pytest.fail("Pillow must not open a mismatched image")
    monkeypatch.setattr(Image, "open", forbidden_decode)
    with pytest.raises(ValueError, match="declared PNG shape"):
        load_target_intensity("header_only.png", grid=_grid())
    assert source.closed


def test_image_same_pixel_count_is_not_same_shape(png_path: Path) -> None:
    with pytest.raises(ValueError, match="declared PNG shape"):
        load_target_intensity(png_path, grid=_grid(3, 2))


def test_image_final_decoded_shape_is_checked(
    png_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_array = np.array
    monkeypatch.setattr(images.np, "array",
                        lambda *a, **k: original_array(*a, **k).reshape(3, 2))
    with pytest.raises(ValueError, match="decoded array shape"):
        load_target_intensity(png_path, grid=_grid())


@pytest.mark.parametrize("content", [b"not PNG", _png()[:33], _png()[:-9]])
def test_image_malformed_or_truncated_rejected(tmp_path: Path, content: bytes) -> None:
    path = tmp_path / "malformed.png"
    path.write_bytes(content)
    with pytest.raises(ValueError, match="malformed.png"):
        load_target_intensity(path, grid=_grid())


def test_image_crc_failure_is_verification_error(tmp_path: Path) -> None:
    content = bytearray(_png())
    content[-13] ^= 1  # last byte of IDAT CRC; IEND is the last 12 bytes
    path = tmp_path / "crc.png"
    path.write_bytes(content)
    with pytest.raises(ValueError, match="integrity verification") as caught:
        load_target_intensity(path, grid=_grid())
    assert isinstance(caught.value.__cause__, SyntaxError)


def test_image_valid_crc_but_bad_pixels_fails_during_decoding(tmp_path: Path) -> None:
    path = tmp_path / "bad_pixels.png"
    path.write_bytes(_png(idat=b"not a zlib stream"))
    with Image.open(path) as image:
        image.verify()  # CRC/integrity pass does not imply successful decoding
    with pytest.raises(ValueError, match="pixel decoding") as caught:
        load_target_intensity(path, grid=_grid())
    assert isinstance(caught.value.__cause__, OSError)
    assert "bad_pixels.png" in str(caught.value)


@pytest.mark.parametrize("bad", [None, 42, b"bytes.png", object()])
def test_image_wrong_path_type(bad) -> None:
    with pytest.raises(TypeError, match="path"):
        load_target_intensity(bad, grid=_grid())


def test_image_bytes_pathlike_rejected() -> None:
    class BytesPath:
        def __fspath__(self):
            return b"bytes.png"
    with pytest.raises(TypeError, match="str"):
        load_target_intensity(BytesPath(), grid=_grid())


def test_image_wrong_grid_type(png_path: Path) -> None:
    with pytest.raises(TypeError, match="grid"):
        load_target_intensity(png_path, grid=(2, 3))


@pytest.mark.parametrize("name", ["absent.png", "."])
def test_image_filesystem_exception_type_preserved(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    with pytest.raises(OSError) as original:
        with open(path, "rb"):
            pass
    with pytest.raises(type(original.value)) as caught:
        load_target_intensity(path, grid=_grid())
    assert caught.value.__cause__ is None


def test_image_read_failure_is_not_a_format_error(monkeypatch: pytest.MonkeyPatch) -> None:
    failure = OSError(5, "simulated device read failure")
    class ReadFailure(BytesIO):
        def read(self, size=-1):
            if size == -1:
                raise failure
            return super().read(size)
    source = ReadFailure(_png())
    monkeypatch.setattr(images, "open", lambda *a: source, raising=False)
    with pytest.raises(OSError) as caught:
        load_target_intensity("read_failure.png", grid=_grid())
    assert caught.value is failure and source.closed


@pytest.mark.parametrize("kind", ["valid", "crc", "pixels", "transparency"])
def test_image_resources_closed_on_success_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    content = _png()
    if kind == "crc":
        content = content[:-13] + bytes([content[-13] ^ 1]) + content[-12:]
    elif kind == "pixels":
        content = _png(idat=b"bad zlib")
    elif kind == "transparency":
        content = _png(extras=((b"tRNS", b"\x00\x00"),))
    path = tmp_path / "handles.png"
    path.write_bytes(content)
    files, streams, opened_images, closed_images = [], [], [], []
    original_open = Image.open
    def track_file(*args):
        result = builtins.open(*args)
        files.append(result)
        return result
    def track_stream(*args):
        result = BytesIO(*args)
        streams.append(result)
        return result
    def track_image(*args, **kwargs):
        result = original_open(*args, **kwargs)
        opened_images.append(result)
        original_close = result.close
        def track_close():
            closed_images.append(result)
            original_close()
        monkeypatch.setattr(result, "close", track_close)
        return result
    monkeypatch.setattr(images, "open", track_file, raising=False)
    monkeypatch.setattr(images, "BytesIO", track_stream)
    monkeypatch.setattr(Image, "open", track_image)
    if kind == "valid":
        load_target_intensity(path, grid=_grid())
    else:
        with pytest.raises(ValueError):
            load_target_intensity(path, grid=_grid())
    assert files and streams and opened_images
    assert all(resource.closed for resource in files + streams)
    assert all(image.fp is None for image in opened_images)
    assert len(closed_images) == len(opened_images)
    assert all(closed is opened for closed, opened in zip(closed_images, opened_images))
    path.unlink()  # also checks Windows source-handle closure


def test_image_keeps_pillow_size_and_truncation_protections(tmp_path: Path) -> None:
    settings = (Image.MAX_IMAGE_PIXELS, ImageFile.LOAD_TRUNCATED_IMAGES)
    width = 2 * Image.MAX_IMAGE_PIXELS + 1
    path = tmp_path / "too_large.png"
    path.write_bytes(_png(width=width, height=1))
    # No huge array is allocated; Pillow rejects the declared pixel count.
    with pytest.raises(Image.DecompressionBombError):
        load_target_intensity(path, grid=_grid(1, width))
    assert settings == (Image.MAX_IMAGE_PIXELS, ImageFile.LOAD_TRUNCATED_IMAGES)


@pytest.mark.parametrize("blocked", ["PIL", "PIL._imaging"])
def test_image_optional_dependency_isolated_in_fresh_process(
    png_path: Path, blocked: str
) -> None:
    code = """
import importlib.abc
import sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == sys.argv[2]:
            raise ModuleNotFoundError('blocked for import isolation', name=fullname)
sys.meta_path.insert(0, Block())
import ohlab
import ohlab.field, ohlab.grid, ohlab.propagation, ohlab.targets
assert not any(n == 'PIL' or n.startswith('PIL.') for n in sys.modules)
assert 'ohlab.io' not in sys.modules
from ohlab.io.images import load_target_intensity
assert not any(n == 'PIL' or n.startswith('PIL.') for n in sys.modules)
grid = ohlab.SamplingGrid(ny=2, nx=3, dy=5e-6, dx=3.74e-6)
try:
    load_target_intensity(sys.argv[1], grid=grid)
except ImportError as exc:
    if sys.argv[2] == 'PIL':
        assert 'ohlab[images]' in str(exc)
        assert exc.__cause__.name == 'PIL'
    else:
        # Python's from-import machinery may present a missing extension as
        # ImportError rather than the finder's ModuleNotFoundError. Preserve
        # that diagnosis instead of relabeling it as an absent optional extra.
        assert '_imaging' in str(exc)
        assert 'ohlab[images]' not in str(exc)
else:
    raise AssertionError('decoding unexpectedly succeeded')
print('import isolation verified')
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(png_path), blocked],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "import isolation verified"
