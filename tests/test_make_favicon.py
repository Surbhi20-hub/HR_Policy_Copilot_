"""Tests for the image maker (needs only Pillow, no Streamlit)."""
from pathlib import Path

from PIL import Image

from src.make_favicon import GREY, SIZE, TEAL, make_avatars, make_favicon


def test_favicon_is_a_64_pixel_teal_square(tmp_path: Path) -> None:
    path = make_favicon(tmp_path / "assets" / "favicon.png")
    image = Image.open(path)
    assert image.size == (SIZE, SIZE) == (64, 64)
    assert image.convert("RGB").getpixel((1, 1)) == TEAL  # the corner is teal, the letters are white


def test_avatars_are_made_in_two_colours(tmp_path: Path) -> None:
    assistant, user = make_avatars(tmp_path / "a.png", tmp_path / "u.png")
    assert Image.open(assistant).convert("RGB").getpixel((1, 1)) == TEAL
    assert Image.open(user).convert("RGB").getpixel((1, 1)) == GREY