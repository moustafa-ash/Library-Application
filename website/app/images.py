"""Shared local JPEG storage for book covers and author photos."""

import io
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4
import warnings

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}


def _directory(kind):
    if kind not in ("books", "authors"):
        raise ValueError("Unknown image kind")
    return Path(current_app.config.get("UPLOAD_ROOT", Path(current_app.instance_path) / "uploads")) / kind


def save_image(upload, kind):
    directory = _directory(kind)
    expected_format = FORMATS.get(Path(upload.filename or "").suffix.lower())
    if expected_format is None:
        raise ValueError("Choose a JPG, PNG, or WebP image.")
    data = upload.stream.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Choose a nonempty image of at most 5 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                if (original.format != expected_format or getattr(original, "is_animated", False)
                        or original.width * original.height > MAX_PIXELS):
                    raise ValueError("Image format, animation, or pixel limit is invalid.")
                original.load()
                oriented = ImageOps.exif_transpose(original)
                oriented.thumbnail((1600, 1600))
                rgba = oriented.convert("RGBA")
                normalized = Image.new("RGB", rgba.size, "white")
                normalized.paste(rgba, mask=rgba.getchannel("A"))
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombWarning,
            Image.DecompressionBombError) as error:
        raise ValueError("Choose a valid, nonanimated image within the pixel limit.") from error

    directory.mkdir(parents=True, exist_ok=True)
    filename = uuid4().hex + ".jpg"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            normalized.save(output, format="JPEG", quality=85)
        os.replace(temporary, directory / filename)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return filename


def delete_image(filename, kind):
    directory = _directory(kind)
    if not isinstance(filename, str) or not re.fullmatch(r"[0-9a-f]{32}\.jpg", filename):
        raise ValueError("Invalid stored image filename")
    (directory / filename).unlink(missing_ok=True)
