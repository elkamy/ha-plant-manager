"""Plant photos stored in the configuration folder and served by the integration."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from homeassistant.core import HomeAssistant

from .species import MAX_IMAGE_BYTES, SpeciesError

IMAGES_DIR = "plant_manager/images"
IMAGES_URL = "/plant_manager/images"
# Only names this module created can be read back or deleted.
_IMAGE_NAME = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp|gif)$")
_SIGNATURES = (
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
)


def images_path(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(IMAGES_DIR))


def image_extension(data: bytes) -> str | None:
    """Return the extension of a JPEG, PNG, GIF or WebP image, from its content."""
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return next((ext for signature, ext in _SIGNATURES if data.startswith(signature)), None)


def _write(directory: Path, data: bytes, extension: str) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}.{extension}"
    (directory / name).write_bytes(data)
    return name


async def async_save_image(hass: HomeAssistant, data: bytes, extension: str) -> str:
    """Store an image and return the URL the cards can display."""
    name = await hass.async_add_executor_job(_write, images_path(hass), data, extension)
    return f"{IMAGES_URL}/{name}"


async def async_save_upload(hass: HomeAssistant, file_id: str) -> str:
    """Store a photo uploaded through the config flow and return its URL."""
    from homeassistant.components.file_upload import process_uploaded_file

    def _copy() -> str:
        with process_uploaded_file(hass, file_id) as path:
            if path.stat().st_size > MAX_IMAGE_BYTES:
                raise SpeciesError("Image too large")
            data = path.read_bytes()
        extension = image_extension(data)
        if extension is None:
            raise SpeciesError("Not a JPEG, PNG, GIF or WebP image")
        return _write(images_path(hass), data, extension)

    return f"{IMAGES_URL}/{await hass.async_add_executor_job(_copy)}"


async def async_delete_image(hass: HomeAssistant, url: str | None) -> None:
    """Delete a photo stored by the integration; other URLs are left alone."""
    if not url or not url.startswith(f"{IMAGES_URL}/"):
        return
    name = url.removeprefix(f"{IMAGES_URL}/").split("?")[0]
    if not _IMAGE_NAME.match(name):
        return
    await hass.async_add_executor_job(
        lambda: (images_path(hass) / name).unlink(missing_ok=True)
    )
