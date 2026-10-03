"""Unit tests for plant photos stored by the integration."""

import asyncio
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path


PACKAGE_PATH = Path(__file__).parents[1] / "custom_components" / "plant_manager"


def load(name):
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    homeassistant.__path__ = getattr(homeassistant, "__path__", [])
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    if not hasattr(core, "HomeAssistant"):
        core.HomeAssistant = object
    package = sys.modules.setdefault(
        "custom_components.plant_manager", types.ModuleType("custom_components.plant_manager")
    )
    package.__path__ = getattr(package, "__path__", [str(PACKAGE_PATH)])
    spec = importlib.util.spec_from_file_location(
        f"custom_components.plant_manager.{name}", PACKAGE_PATH / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


load("species")
IMAGES = load("images")


class FakeHass:
    def __init__(self, config_dir):
        self.config = types.SimpleNamespace(path=lambda *parts: str(Path(config_dir, *parts)))

    async def async_add_executor_job(self, function, *args):
        return function(*args)


class ImageExtensionTests(unittest.TestCase):
    def test_recognises_supported_formats_from_their_content(self):
        self.assertEqual(IMAGES.image_extension(b"\xff\xd8\xff\xe0rest"), "jpg")
        self.assertEqual(IMAGES.image_extension(b"\x89PNG\r\n\x1a\nrest"), "png")
        self.assertEqual(IMAGES.image_extension(b"GIF89arest"), "gif")
        self.assertEqual(IMAGES.image_extension(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "webp")

    def test_rejects_other_files(self):
        for data in (b"<svg/>", b"%PDF-1.7", b"RIFF\x00\x00\x00\x00WAVE", b""):
            with self.subTest(data=data):
                self.assertIsNone(IMAGES.image_extension(data))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.hass = FakeHass(self.tmp.name)
        self.folder = Path(self.tmp.name, "plant_manager", "images")

    def test_saves_under_a_unique_name_served_by_the_integration(self):
        url = asyncio.run(IMAGES.async_save_image(self.hass, b"\xff\xd8\xffphoto", "jpg"))
        self.assertRegex(url, r"^/plant_manager/images/[0-9a-f]{32}\.jpg$")
        self.assertEqual((self.folder / url.rsplit("/", 1)[1]).read_bytes(), b"\xff\xd8\xffphoto")

    def test_deletes_only_its_own_photos(self):
        url = asyncio.run(IMAGES.async_save_image(self.hass, b"\xff\xd8\xff", "jpg"))
        outside = Path(self.tmp.name, "secrets.yaml")
        outside.write_text("keep")
        for other in (
            "/local/plant.jpg",
            "https://example.com/plant.jpg",
            "/plant_manager/images/../../secrets.yaml",
            "/plant_manager/images/secrets.yaml",
            "",
            None,
        ):
            asyncio.run(IMAGES.async_delete_image(self.hass, other))
        self.assertTrue(outside.exists())
        self.assertTrue((self.folder / url.rsplit("/", 1)[1]).exists())

        asyncio.run(IMAGES.async_delete_image(self.hass, url))
        self.assertFalse((self.folder / url.rsplit("/", 1)[1]).exists())
        # Deleting again is harmless.
        asyncio.run(IMAGES.async_delete_image(self.hass, url))


if __name__ == "__main__":
    unittest.main()
