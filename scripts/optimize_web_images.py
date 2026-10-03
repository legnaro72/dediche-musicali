"""Riduce il peso delle immagini WebP già pubblicate senza cambiare percorsi o dimensioni."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "public" / "images" / "dedications"
MIN_BYTES = 200_000
QUALITY = 84
MIN_SAVING_RATIO = 0.08


def optimize(path: Path) -> tuple[int, int] | None:
    original = path.read_bytes()
    if len(original) < MIN_BYTES:
        return None

    with Image.open(io.BytesIO(original)) as source:
        frame = source.convert("RGB")
        output = io.BytesIO()
        frame.save(output, "WEBP", quality=QUALITY, method=6)

    optimized = output.getvalue()
    if len(optimized) >= len(original) * (1 - MIN_SAVING_RATIO):
        return None

    path.write_bytes(optimized)
    return len(original), len(optimized)


def main() -> None:
    changed = 0
    saved = 0
    for path in sorted(IMAGE_DIR.glob("*.webp")):
        result = optimize(path)
        if not result:
            continue
        before, after = result
        changed += 1
        saved += before - after
        print(f"{path.name}: {before // 1024} KB -> {after // 1024} KB")
    print(f"Ottimizzate {changed} immagini; risparmiati {saved / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
