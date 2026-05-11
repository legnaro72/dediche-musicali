"""
publish_daily.py — Pubblica la dedica del giorno.

Legge il Google Sheet (o i JSON locali), trova la dedica del giorno,
la valida, genera l'immagine, aggiorna lo stato e prepara il sito.

Uso:
    python scripts/publish_daily.py
    python scripts/publish_daily.py --date 2026-05-12
    python scripts/publish_daily.py --date 2026-05-12 --force-republish
    python scripts/publish_daily.py --date 2026-05-12 --dry-run
"""
import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import (
    setup_logging, get_rome_today, parse_date, load_json, save_json,
    get_dedication_json_path, load_all_dedications, get_rome_now, ROME_TZ,
)

logger = setup_logging('publish')


def find_todays_dedication(date_str: str):
    """Cerca la dedica per la data indicata (status=scheduled o published)."""
    path = get_dedication_json_path(date_str)
    if path.exists():
        ded = load_json(path)
        if ded and ded.get('status') in ('scheduled', 'published'):
            return ded
    # fallback: cerca in tutti i JSON
    for ded in load_all_dedications():
        if ded.get('date') == date_str and ded.get('status') in ('scheduled', 'published'):
            return ded
    return None


def find_latest_published():
    """Trova l'ultima dedica pubblicata (per fallback homepage)."""
    today = get_rome_today()
    candidates = []
    for ded in load_all_dedications():
        if ded.get('status') == 'published' and ded.get('date', '') <= today:
            candidates.append(ded)
    if not candidates:
        return None
    return sorted(candidates, key=lambda d: d.get('date', ''))[-1]


def mark_as_published(ded: dict, dry_run: bool = False) -> bool:
    """Aggiorna lo status a 'published' e updated_at."""
    ded['status'] = 'published'
    ded['updated_at'] = get_rome_now().isoformat()

    if dry_run:
        logger.info(f"  [DRY RUN] Aggiornerebbe status → published: {ded['id']}")
        return True

    path = get_dedication_json_path(ded['date'])
    return save_json(ded, path)


def write_today_json(ded: dict, dry_run: bool = False) -> bool:
    """Scrive il file today.json per il frontend."""
    from scripts.utils import ROOT_DIR
    today_path = ROOT_DIR / 'data' / 'today.json'

    if dry_run:
        logger.info(f"  [DRY RUN] Scriverebbe data/today.json")
        return True

    return save_json(ded, today_path)


def publish(date_str: str, force_republish: bool = False, dry_run: bool = False) -> bool:
    logger.info(f"Data target: {date_str} (Europe/Rome)")

    # 1. Cerca la dedica
    ded = find_todays_dedication(date_str)
    if not ded:
        logger.warning(f"⚠ Nessuna dedica trovata per {date_str}. Il sito resta invariato.")
        return True  # non è un errore: il sito resta online

    ded_id = ded.get('id', '?')
    logger.info(f"Trovata: {ded_id} [{ded.get('status')}]")

    # 2. Controlla se già pubblicata
    if ded.get('status') == 'published' and not force_republish:
        logger.info(f"✓ Dedica {ded_id} già pubblicata. Usa --force-republish per forzare.")
        write_today_json(ded, dry_run)
        return True

    # 3. Valida
    from scripts.validate_dedications import validate_dedication
    errors = validate_dedication(ded, set(), {})
    if errors:
        logger.error(f"❌ Validazione fallita per {ded_id}:")
        for e in errors:
            logger.error(f"   ✗ {e}")
        return False

    # 4. Genera immagine
    logger.info("Generazione immagine...")
    from scripts.generate_image import ensure_fonts, generate_for_dedication
    fonts = ensure_fonts()
    img_ok = generate_for_dedication(ded, fonts, dry_run=dry_run)
    if not img_ok:
        logger.error("❌ Generazione immagine fallita")
        return False

    # 5. Aggiorna stato → published
    if not mark_as_published(ded, dry_run):
        logger.error("❌ Impossibile aggiornare stato dedica")
        return False

    # 6. Scrivi today.json
    if not write_today_json(ded, dry_run):
        logger.error("❌ Impossibile scrivere today.json")
        return False

    logger.info(f"✅ Dedica '{ded_id}' pubblicata con successo per {date_str}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Pubblica la dedica del giorno')
    parser.add_argument('--date', default=None, help='Data (YYYY-MM-DD), default: oggi Rome')
    parser.add_argument('--force-republish', action='store_true', help='Forza ripubblicazione')
    parser.add_argument('--dry-run', action='store_true', help='Simula senza scrivere')
    args = parser.parse_args()

    date_str = args.date or get_rome_today()
    logger.info("=== Pubblicazione giornaliera DDGPilliSite ===")

    ok = publish(date_str, force_republish=args.force_republish, dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
