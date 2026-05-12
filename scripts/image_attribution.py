"""
image_attribution.py — Salva metadati di attribuzione per le immagini.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger('generate_image')

ATTR_DIR = Path(__file__).parent.parent / 'data' / 'image-attributions'


def save_attribution(date_str: str, attribution: dict) -> None:
    """Salva il file attribution JSON per la dedica."""
    if not attribution:
        return
    ATTR_DIR.mkdir(parents=True, exist_ok=True)
    path = ATTR_DIR / f'{date_str}.json'
    data = {'date': date_str, **attribution}
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f'    Attribution salvata: {path.name}')
    except Exception as e:
        logger.warning(f'    Attribution non salvata: {e}')


def load_attribution(date_str: str) -> dict:
    """Carica attribution esistente (se presente)."""
    path = ATTR_DIR / f'{date_str}.json'
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}
