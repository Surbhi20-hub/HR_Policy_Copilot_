"""Make the small images of the app: the browser-tab icon and the two chat avatars.

Run once from the project root:  python -m src.make_favicon
It writes three PNG files into assets/ (only Pillow is used, no emoji, no downloads):
  favicon.png          teal square with the white letters HR (64 x 64)
  avatar_assistant.png teal square with HR (the copilot)
  avatar_user.png      grey square with the letter U (the employee)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.config import ROOT_DIR

ASSETS_DIR = ROOT_DIR / "assets"
FAVICON_FILE = ASSETS_DIR / "favicon.png"
ASSISTANT_AVATAR_FILE = ASSETS_DIR / "avatar_assistant.png"
USER_AVATAR_FILE = ASSETS_DIR / "avatar_user.png"
SIZE = 64
TEAL = (15, 118, 110)  # #0F766E
GREY = (100, 116, 139)  # #64748B, readable on both light and dark pages
WHITE = (255, 255, 255)


def make_badge(path: Path, text: str, color: tuple[int, int, int], font_size: int = 32) -> Path:
    """Draw white `text` in the middle of a square of `color`, save it as a PNG, return the path."""
    image = Image.new("RGB", (SIZE, SIZE), color)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default(size=font_size)  # Pillow 10.1 or newer: a built-in font that can grow
    except TypeError:
        font = ImageFont.load_default()  # older Pillow: a small fixed size, still readable
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    x = (SIZE - (right - left)) / 2 - left  # shift so the letters sit in the middle
    y = (SIZE - (bottom - top)) / 2 - top
    draw.text((x, y), text, font=font, fill=WHITE)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def make_favicon(path: Path = FAVICON_FILE) -> Path:
    """The browser-tab icon: white HR on teal."""
    return make_badge(path, "HR", TEAL)


def make_avatars(assistant_path: Path = ASSISTANT_AVATAR_FILE, user_path: Path = USER_AVATAR_FILE) -> list[Path]:
    """The two chat avatars (letters, not emoji)."""
    return [make_badge(assistant_path, "HR", TEAL), make_badge(user_path, "U", GREY, font_size=36)]


if __name__ == "__main__":
    for saved in [make_favicon(), *make_avatars()]:
        print(f"Saved {saved}")