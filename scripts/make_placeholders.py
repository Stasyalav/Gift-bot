"""Генерация простых картинок-заглушек для приветствия.

Это не обязательный шаг: можно просто положить в `assets/greetings/`
свои фотографии 1200x800 (jpg/png). Скрипт нужен, чтобы проект
запускался «из коробки» без готовых картинок.

Запуск:
    .\\.venv\\Scripts\\python.exe scripts\\make_placeholders.py
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw

WIDTH, HEIGHT = 1200, 800
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "greetings"

PALETTES = [
    # (фон сверху, фон снизу, коробка, лента, акцент)
    ("#F7EFE6", "#EAD9CC", "#E8C4C4", "#C9A86A", "#4A3428"),
    ("#E8C4C4", "#D9A7A7", "#F7EFE6", "#4A3428", "#C9A86A"),
    ("#4A3428", "#2E2019", "#C9A86A", "#F7EFE6", "#E8C4C4"),
    ("#F7EFE6", "#E8C4C4", "#C9A86A", "#4A3428", "#D9A7A7"),
    ("#EAD9CC", "#C9A86A", "#4A3428", "#F7EFE6", "#E8C4C4"),
    ("#F7EFE6", "#F0E2D6", "#D9A7A7", "#C9A86A", "#4A3428"),
]


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def gradient(top: str, bottom: str) -> Image.Image:
    top_rgb = hex_to_rgb(top)
    bottom_rgb = hex_to_rgb(bottom)
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        color = tuple(
            round(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * ratio) for i in range(3)
        )
        draw.line([(0, y), (WIDTH, y)], fill=color)
    return image


def draw_gift(
    draw: ImageDraw.ImageDraw,
    box_color: str,
    ribbon_color: str,
    accent_color: str,
    cx: int,
    cy: int,
    scale: float,
) -> None:
    box_w = int(360 * scale)
    box_h = int(260 * scale)
    left = cx - box_w // 2
    top = cy - box_h // 2
    right = cx + box_w // 2
    bottom = cy + box_h // 2

    # Коробка
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=int(28 * scale),
        fill=box_color,
    )

    # Крышка
    lid_h = int(78 * scale)
    draw.rounded_rectangle(
        [left - int(18 * scale), top - lid_h // 2, right + int(18 * scale), top + lid_h // 2],
        radius=int(18 * scale),
        fill=box_color,
    )

    # Вертикальная лента
    ribbon_w = int(46 * scale)
    draw.rectangle(
        [cx - ribbon_w // 2, top - lid_h // 2, cx + ribbon_w // 2, bottom],
        fill=ribbon_color,
    )

    # Горизонтальная лента на крышке
    draw.rectangle(
        [left - int(18 * scale), top - int(12 * scale), right + int(18 * scale), top + int(12 * scale)],
        fill=ribbon_color,
    )

    # Бантик
    bow_r = int(52 * scale)
    draw.ellipse(
        [cx - bow_r * 2, top - lid_h // 2 - bow_r, cx - int(8 * scale), top - lid_h // 2 + bow_r // 2],
        fill=ribbon_color,
    )
    draw.ellipse(
        [cx + int(8 * scale), top - lid_h // 2 - bow_r, cx + bow_r * 2, top - lid_h // 2 + bow_r // 2],
        fill=ribbon_color,
    )
    draw.ellipse(
        [cx - int(16 * scale), top - lid_h // 2 - int(16 * scale), cx + int(16 * scale), top - lid_h // 2 + int(16 * scale)],
        fill=accent_color,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    for index, (bg_top, bg_bottom, box, ribbon, accent) in enumerate(PALETTES, start=1):
        image = gradient(bg_top, bg_bottom)
        draw = ImageDraw.Draw(image)

        # Крупные полупрозрачные круги для «мягкости»
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        for _ in range(3):
            r = random.randint(90, 190)
            x = random.randint(-r, WIDTH + r)
            y = random.randint(-r, HEIGHT + r)
            overlay_draw.ellipse(
                [x - r, y - r, x + r, y + r],
                fill=(*hex_to_rgb(accent), random.randint(10, 24)),
            )
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)

        cx = WIDTH // 2 + random.randint(-120, 120)
        cy = HEIGHT // 2 + random.randint(-40, 60)
        draw_gift(draw, box, ribbon, accent, cx, cy, scale=random.uniform(0.95, 1.15))

        path = OUT_DIR / f"{index:02d}.jpg"
        image.save(path, "JPEG", quality=86, optimize=True)
        print(f"{path.name}: {path.stat().st_size // 1024} КБ")


if __name__ == "__main__":
    main()
