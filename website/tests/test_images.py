import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from werkzeug.datastructures import FileStorage

from app import create_app
from app.images import save_image, delete_image
from tests import TEST_CONFIG


def upload(format="PNG", mode="RGBA", size=(20, 30), filename=None, **options):
    data = io.BytesIO()
    image = Image.new(mode, size, (0, 0, 0, 0) if mode == "RGBA" else "red")
    image.save(data, format=format, **options)
    data.seek(0)
    return FileStorage(data, filename=filename or "test." + format.lower())


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.app = create_app({**TEST_CONFIG, "SESSION_FILE_DIR": str(self.root / "sessions"),
                               "UPLOAD_ROOT": str(self.root / "uploads")})
        self.context = self.app.app_context()
        self.context.push()
        self.addCleanup(self.context.pop)

    def test_formats_become_generated_rgb_jpegs(self):
        for format in ("PNG", "JPEG", "WEBP"):
            with self.subTest(format=format):
                name = save_image(upload(format, "RGB"), "books")
                self.assertRegex(name, r"^[0-9a-f]{32}\.jpg$")
                with Image.open(self.root / "uploads/books" / name) as image:
                    self.assertEqual((image.format, image.mode, image.size), ("JPEG", "RGB", (20, 30)))
                    self.assertFalse(image.getexif())
                delete_image(name, "books")
                delete_image(name, "books")

    def test_transparency_resize_orientation_and_metadata(self):
        name = save_image(upload(size=(2000, 1000)), "authors")
        with Image.open(self.root / "uploads/authors" / name) as image:
            self.assertEqual(image.size, (1600, 800))
            self.assertTrue(all(channel > 250 for channel in image.getpixel((0, 0))))
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "private author"
        name = save_image(upload("JPEG", "RGB", (20, 30), exif=exif), "books")
        with Image.open(self.root / "uploads/books" / name) as image:
            self.assertEqual(image.size, (30, 20))
            self.assertFalse(image.getexif())

    def test_reject_invalid_formats_content_and_animation(self):
        animated = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(animated, format="PNG", save_all=True,
            append_images=[Image.new("RGB", (10, 10), "blue")])
        cases = [upload(filename="fake.jpg"), upload("GIF", "RGB"),
                 FileStorage(io.BytesIO(b""), filename="empty.png"),
                 FileStorage(io.BytesIO(b"not an image"), filename="bad.png"),
                 FileStorage(io.BytesIO(animated.getvalue()), filename="animated.png"),
                 upload(filename="picture.svg"),
                 FileStorage(io.BytesIO(b"x" * (5 * 1024 * 1024 + 1)), filename="big.jpg")]
        for item in cases:
            with self.subTest(filename=item.filename), self.assertRaises(ValueError):
                save_image(item, "books")
        truncated = upload("JPEG", "RGB").stream.getvalue()[:-20]
        with self.assertRaises(ValueError):
            save_image(FileStorage(io.BytesIO(truncated), filename="cut.jpg"), "books")
        self.assertFalse((self.root / "uploads/books").exists())

    def test_pixel_and_bomb_limits(self):
        with self.assertRaises(ValueError):
            save_image(upload(size=(5000, 4001)), "books")
        with patch("PIL.Image.MAX_IMAGE_PIXELS", 100), self.assertRaises(ValueError):
            save_image(upload(size=(11, 10)), "books")

    def test_safe_deletion_and_failed_write_cleanup(self):
        for kind, name in [("../books", "a" * 32 + ".jpg"), ("books", "../outside.jpg"),
                           ("books", "wrong.jpg"), ("books", "/tmp/test.jpg")]:
            with self.subTest(kind=kind, name=name), self.assertRaises(ValueError):
                delete_image(name, kind)
        with self.assertRaises(ValueError):
            save_image(upload(), "invalid")
        with patch("app.images.os.replace", side_effect=OSError("disk failure")), self.assertRaises(OSError):
            save_image(upload(), "books")
        self.assertEqual(list((self.root / "uploads/books").iterdir()), [])
