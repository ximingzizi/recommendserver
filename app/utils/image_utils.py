from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image


COLOR_MAP = {
    "白色": (235, 235, 230),
    "黑色": (40, 40, 40),
    "蓝色": (70, 115, 190),
    "红色": (190, 75, 75),
    "绿色": (90, 150, 110),
    "卡其色": (180, 160, 120),
    "杏色": (220, 195, 170),
    "米色": (214, 201, 180),
}


def save_bytes_to_file(content: bytes, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return destination


def infer_dominant_color(image_bytes: bytes) -> str:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((128, 128))
    pixels = list(image.getdata())
    red = sum(pixel[0] for pixel in pixels) / len(pixels)
    green = sum(pixel[1] for pixel in pixels) / len(pixels)
    blue = sum(pixel[2] for pixel in pixels) / len(pixels)

    def distance(reference: tuple[int, int, int]) -> float:
        return ((red - reference[0]) ** 2 + (green - reference[1]) ** 2 + (blue - reference[2]) ** 2) ** 0.5

    return min(COLOR_MAP, key=lambda name: distance(COLOR_MAP[name]))
