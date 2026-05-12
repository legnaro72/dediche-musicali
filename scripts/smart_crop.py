"""
smart_crop.py — Crop intelligente con bias compositivo.
Preserva cielo, volti e soggetti. Evita tagli aggressivi.
"""
import logging
logger = logging.getLogger('generate_image')


def is_landscape(img) -> bool:
    """True se l'immagine è orizzontale (larghezza > altezza * 1.1)."""
    return img.width > img.height * 1.1


def smart_vertical_crop(img, target_w: int = 1080, target_h: int = 1350):
    """
    Crop verticale 1080x1350 con upper-middle bias.
    Preferisce la parte alta per preservare cielo e volti.
    """
    from PIL import Image
    src_w, src_h = img.size
    tgt_ratio = target_w / target_h
    src_ratio = src_w / src_h
    logger.info(f'    Portrait crop → {target_w}x{target_h}')
    if src_ratio > tgt_ratio:
        # Immagine più larga: crop laterale centrato
        new_w = int(src_h * tgt_ratio)
        x = (src_w - new_w) // 2
        img = img.crop((x, 0, x + new_w, src_h))
    else:
        # Immagine più alta: crop verticale, bias superiore max 15%
        new_h = int(src_w / tgt_ratio)
        y = min(max(0, src_h - new_h), int(src_h * 0.15))
        img = img.crop((0, y, src_w, y + new_h))
    return img.resize((target_w, target_h), Image.LANCZOS)


def smart_og_crop(img, target_w: int = 1200, target_h: int = 630):
    """
    Smart crop OpenGraph 1200x630 con upper-middle bias.
    - Portrait → landscape: safe area superiore (bias 20%)
    - Se crop > 60% dell'immagine: contain + soft blurred background
    - Landscape: crop laterale centrato
    """
    from PIL import Image
    src_w, src_h = img.size
    tgt_ratio = target_w / target_h
    src_ratio = src_w / src_h
    logger.info('    Smart OG crop → 1200x630 (upper-middle bias)')

    if src_ratio >= tgt_ratio:
        # Già landscape / quadrata — crop laterale centrato
        new_w = int(src_h * tgt_ratio)
        x = (src_w - new_w) // 2
        cropped = img.crop((x, 0, x + new_w, src_h))
    else:
        # Portrait → landscape
        new_h = int(src_w / tgt_ratio)
        crop_ratio = new_h / src_h

        if crop_ratio < 0.40:
            # Crop troppo aggressivo (> 60% tagliato) — usa contain mode
            logger.info('    OG: crop aggressivo rilevato → contain con soft background')
            return _og_contain(img, target_w, target_h)

        # Bias superiore: preserva top 20% dell'immagine
        y_max  = src_h - new_h
        y_bias = min(y_max, int(src_h * 0.20))
        pct    = 100 - int(y_bias / src_h * 100)
        logger.info(f'    Safe area: y_bias={y_bias}px (top {pct}% preservato)')
        cropped = img.crop((0, y_bias, src_w, y_bias + new_h))

    return cropped.resize((target_w, target_h), Image.LANCZOS)


def _og_contain(img, target_w: int, target_h: int):
    """
    Contain mode: immagine intera su sfondo sfumato dall'immagine stessa.
    Evita qualsiasi taglio quando il crop sarebbe distruttivo.
    """
    from PIL import Image, ImageFilter, ImageEnhance
    # Background sfumato e scurito
    bg = img.resize((target_w, target_h), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
    bg = ImageEnhance.Brightness(bg).enhance(0.35)

    # Foreground: fit letterbox
    img_ratio = img.width / img.height
    tgt_ratio  = target_w / target_h
    if img_ratio > tgt_ratio:
        fit_w = target_w
        fit_h = int(target_w / img_ratio)
    else:
        fit_h = target_h
        fit_w = int(target_h * img_ratio)

    fg = img.resize((fit_w, fit_h), Image.LANCZOS)
    result = bg.copy()
    result.paste(fg, ((target_w - fit_w) // 2, (target_h - fit_h) // 2))
    return result
