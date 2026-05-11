"""
generate_image.py — Genera le immagini grafiche per le dediche.

Genera:
  - 1080x1350 px  (verticale, social/mobile)
  - 1200x630  px  (OpenGraph)

Uso:
    python scripts/generate_image.py --date 2026-05-12
    python scripts/generate_image.py --all
"""
import sys
import os
import math
import urllib.request
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import (
    setup_logging, load_all_dedications, load_json, get_dedication_json_path,
    get_italian_day_name, format_date_italian, IMAGES_DIR, FONTS_DIR,
)

logger = setup_logging('generate_image')

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DARK    = (10, 8, 20)
PURPLE_1   = (124, 58, 237)
PURPLE_2   = (190, 50, 200)
MAGENTA    = (236, 72, 153)
BLUE_DEEP  = (30, 27, 75)
WHITE      = (255, 255, 255)
WHITE_DIM  = (200, 190, 240)
ACCENT     = (167, 139, 250)

FONT_URLS = {
    'bold':    'https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf',
    'regular': 'https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Regular.ttf',
    'italic':  'https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Italic.ttf',
}


def ensure_fonts() -> dict:
    """Scarica i font se non presenti. Restituisce dizionario path -> str."""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, url in FONT_URLS.items():
        dest = FONTS_DIR / f'Montserrat-{name.capitalize()}.ttf'
        if not dest.exists():
            logger.info(f"Download font {name}...")
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception as e:
                logger.warning(f"Font {name} non scaricato: {e}")
                paths[name] = None
                continue
        paths[name] = str(dest)
    return paths


def get_font(fonts: dict, style: str, size: int):
    from PIL import ImageFont
    path = fonts.get(style)
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_gradient(img, c1, c2, c3=None):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = y / h
        if c3 and t > 0.5:
            t2 = (t - 0.5) * 2
            r = int(c2[0] + (c3[0] - c2[0]) * t2)
            g = int(c2[1] + (c3[1] - c2[1]) * t2)
            b = int(c2[2] + (c3[2] - c2[2]) * t2)
        else:
            t1 = t * 2 if c3 else t
            t1 = min(t1, 1.0)
            r = int(c1[0] + (c2[0] - c1[0]) * t1)
            g = int(c1[1] + (c2[1] - c1[1]) * t1)
            b = int(c1[2] + (c2[2] - c1[2]) * t1)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def draw_glow_circle(draw, cx, cy, radius, color, alpha_start=80):
    for i in range(radius, 0, -max(1, radius // 20)):
        a = int(alpha_start * (i / radius) ** 2)
        draw.ellipse(
            [cx - i, cy - i, cx + i, cy + i],
            fill=(*color, a)
        )


def wrap_text(text: str, font, max_width: int, draw) -> list:
    """Wrappa il testo in righe che non superano max_width."""
    words = text.split()
    lines = []
    current = ''
    for word in words:
        test = (current + ' ' + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_vertical(ded: dict, fonts: dict) -> 'Image':
    """Genera immagine 1080x1350 (verticale social)."""
    from PIL import Image, ImageDraw, ImageFilter

    W, H = 1080, 1350
    img = Image.new('RGBA', (W, H))
    draw_gradient(img, BG_DARK, BLUE_DEEP, (20, 5, 40))

    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    draw_glow_circle(odraw, int(W * 0.15), int(H * 0.15), 350, PURPLE_1, 60)
    draw_glow_circle(odraw, int(W * 0.85), int(H * 0.75), 280, MAGENTA, 50)
    draw_glow_circle(odraw, int(W * 0.5), int(H * 0.5), 200, PURPLE_2, 30)
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)

    # Linea decorativa superiore
    for i in range(4):
        alpha = 200 - i * 40
        draw.line([(60, 80 + i), (W - 60, 80 + i)], fill=(*ACCENT, alpha), width=1)

    # Data e giorno
    font_date = get_font(fonts, 'regular', 36)
    date_str = ded.get('date', '')
    day_name = get_italian_day_name(date_str)
    date_it = format_date_italian(date_str)
    date_text = f"{day_name.upper()}  ·  {date_it.upper()}"
    draw.text((W // 2, 130), date_text, font=font_date, fill=(*ACCENT, 220), anchor='mm')

    # Icona musicale decorativa
    font_icon = get_font(fonts, 'bold', 80)
    draw.text((W // 2, 240), '♪', font=font_icon, fill=(*WHITE, 40), anchor='mm')

    # Titolo canzone
    font_title = get_font(fonts, 'bold', 72)
    song = ded.get('song_title', '')
    song_lines = wrap_text(song, font_title, W - 120, draw)
    y = 380
    for line in song_lines[:3]:
        draw.text((W // 2, y), line, font=font_title, fill=WHITE, anchor='mm')
        y += 90

    # Artista
    font_artist = get_font(fonts, 'italic', 44)
    draw.text((W // 2, y + 20), ded.get('artist', ''), font=font_artist,
              fill=(*MAGENTA, 230), anchor='mm')
    y += 90

    # Separatore
    sep_y = y + 40
    draw.line([(W // 2 - 80, sep_y), (W // 2 + 80, sep_y)], fill=(*ACCENT, 150), width=2)

    # Frase breve
    phrase = ded.get('short_phrase', '') or ded.get('dedication_title', '')
    if phrase:
        font_phrase = get_font(fonts, 'italic', 38)
        phrase_lines = wrap_text(phrase, font_phrase, W - 160, draw)
        y2 = sep_y + 60
        for line in phrase_lines[:4]:
            draw.text((W // 2, y2), line, font=font_phrase, fill=(*WHITE_DIM, 200), anchor='mm')
            y2 += 54

    # Nome sito in basso
    font_site = get_font(fonts, 'bold', 30)
    site_name = os.environ.get('SITE_NAME', 'DDGPilliSite')
    draw.text((W // 2, H - 80), f'✦ {site_name} ✦', font=font_site,
              fill=(*ACCENT, 180), anchor='mm')

    # Linea decorativa inferiore
    draw.line([(60, H - 110), (W - 60, H - 110)], fill=(*ACCENT, 100), width=1)

    return img.convert('RGB')


def generate_og(ded: dict, fonts: dict) -> 'Image':
    """Genera immagine 1200x630 (OpenGraph)."""
    from PIL import Image, ImageDraw

    W, H = 1200, 630
    img = Image.new('RGBA', (W, H))
    draw_gradient(img, BG_DARK, (20, 10, 50), BLUE_DEEP)

    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    draw_glow_circle(odraw, 100, 100, 250, PURPLE_1, 50)
    draw_glow_circle(odraw, W - 100, H - 100, 200, MAGENTA, 40)
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)

    # Titolo canzone
    font_title = get_font(fonts, 'bold', 64)
    song = ded.get('song_title', '')
    song_lines = wrap_text(song, font_title, W - 120, draw)
    y = 180
    for line in song_lines[:2]:
        draw.text((W // 2, y), line, font=font_title, fill=WHITE, anchor='mm')
        y += 80

    # Artista
    font_artist = get_font(fonts, 'italic', 40)
    draw.text((W // 2, y + 20), ded.get('artist', ''), font=font_artist,
              fill=(*MAGENTA, 220), anchor='mm')

    # Data
    font_date = get_font(fonts, 'regular', 28)
    date_it = format_date_italian(ded.get('date', ''))
    draw.text((W // 2, H - 80), date_it.upper(), font=font_date,
              fill=(*ACCENT, 200), anchor='mm')

    # Nome sito
    font_site = get_font(fonts, 'bold', 26)
    site_name = os.environ.get('SITE_NAME', 'DDGPilliSite')
    draw.text((80, 60), site_name, font=font_site, fill=(*ACCENT, 200), anchor='lm')

    return img.convert('RGB')


def generate_for_dedication(ded: dict, fonts: dict, dry_run: bool = False) -> bool:
    """Genera entrambe le immagini per una dedica."""
    date_str = ded.get('date', '')
    if not date_str:
        logger.error("Dedica senza data")
        return False

    image_mode = ded.get('image', {}).get('mode', ded.get('image_mode', 'auto'))
    if image_mode == 'none':
        logger.info(f"  SKIP (image_mode=none): {date_str}")
        return True
    if image_mode == 'upload':
        logger.info(f"  SKIP (image_mode=upload): {date_str}")
        return True

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    vertical_path = IMAGES_DIR / f'{date_str}.webp'
    og_path = IMAGES_DIR / f'{date_str}-og.webp'

    if dry_run:
        logger.info(f"  [DRY RUN] Genererebbe: {vertical_path.name}, {og_path.name}")
        return True

    try:
        logger.info(f"  Generazione immagini per {date_str}...")
        v_img = generate_vertical(ded, fonts)
        v_img.save(str(vertical_path), 'WEBP', quality=90)
        logger.info(f"    ✓ {vertical_path.name}")

        og_img = generate_og(ded, fonts)
        og_img.save(str(og_path), 'WEBP', quality=90)
        logger.info(f"    ✓ {og_path.name}")
        return True

    except Exception as e:
        logger.error(f"  ✗ Errore generazione immagini per {date_str}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Genera immagini dediche')
    parser.add_argument('--date', help='Data specifica (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='Genera per tutte le dediche pubblicate')
    parser.add_argument('--dry-run', action='store_true', help='Non scrivere file')
    args = parser.parse_args()

    logger.info("=== Generazione immagini DDGPilliSite ===")
    fonts = ensure_fonts()

    if args.date:
        path = get_dedication_json_path(args.date)
        ded = load_json(path)
        if not ded:
            logger.error(f"Dedica non trovata: {args.date}")
            sys.exit(1)
        ok = generate_for_dedication(ded, fonts, dry_run=args.dry_run)
        sys.exit(0 if ok else 1)

    elif args.all:
        dedications = load_all_dedications()
        errors = 0
        for ded in dedications:
            if ded.get('status') in ('published', 'scheduled'):
                if not generate_for_dedication(ded, fonts, dry_run=args.dry_run):
                    errors += 1
        sys.exit(0 if errors == 0 else 1)

    else:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()
