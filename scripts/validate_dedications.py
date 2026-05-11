"""
validate_dedications.py — Valida le dediche prima del deploy.

Uso:
    python scripts/validate_dedications.py
    python scripts/validate_dedications.py --strict   # blocca anche su warning
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import (
    setup_logging, load_all_dedications, is_valid_url,
    parse_date, VALID_STATUSES, VALID_IMAGE_MODES, VALID_AUDIO_TYPES,
)

logger = setup_logging('validate')


def validate_dedication(ded: dict, seen_ids: set, active_dates: dict) -> list:
    """Restituisce una lista di messaggi di errore per la dedica."""
    errors = []
    ded_id = ded.get('id', '').strip()

    # id
    if not ded_id:
        errors.append("Campo 'id' mancante")
    elif ded_id in seen_ids:
        errors.append(f"ID duplicato: '{ded_id}'")
    elif not re.match(r'^[a-z0-9\-]+$', ded_id) if __import__('re').match else False:
        errors.append(f"ID '{ded_id}' non valido (solo lettere minuscole, numeri, trattini)")

    # date
    date = ded.get('date', '').strip()
    if not date:
        errors.append("Campo 'date' mancante")
    elif not parse_date(date):
        errors.append(f"Data '{date}' non nel formato YYYY-MM-DD")

    # status
    status = ded.get('status', '').strip()
    if not status:
        errors.append("Campo 'status' mancante")
    elif status not in VALID_STATUSES:
        errors.append(f"Status '{status}' non valido. Ammessi: {sorted(VALID_STATUSES)}")

    # controlla date duplicate per dediche attive
    if date and status in ('scheduled', 'published'):
        if date in active_dates:
            errors.append(f"Data {date} già usata da '{active_dates[date]}'")
        else:
            active_dates[date] = ded_id

    # campi testo obbligatori
    for field in ['song_title', 'artist', 'dedication_title', 'dedication_text']:
        if not ded.get(field, '').strip():
            errors.append(f"Campo '{field}' mancante o vuoto")

    # audio_url
    audio_url = ded.get('audio_url', '').strip()
    if not audio_url:
        errors.append("Campo 'audio_url' mancante")
    elif not is_valid_url(audio_url):
        errors.append(f"audio_url non è un URL https valido: '{audio_url}'")

    # audio_type
    audio_type = ded.get('audio_type', '').strip()
    if audio_type and audio_type not in VALID_AUDIO_TYPES:
        errors.append(f"audio_type '{audio_type}' non valido. Ammessi: {sorted(VALID_AUDIO_TYPES)}")

    # image_mode
    image_mode = ded.get('image_mode', 'auto').strip()
    if image_mode and image_mode not in VALID_IMAGE_MODES:
        errors.append(f"image_mode '{image_mode}' non valido. Ammessi: {sorted(VALID_IMAGE_MODES)}")

    # vote_url
    vote_url = ded.get('vote_url', '').strip()
    default_vote_url = os.environ.get('DEFAULT_VOTE_URL', '').strip()
    if not vote_url and not default_vote_url:
        errors.append("vote_url vuoto e DEFAULT_VOTE_URL non configurato")
    elif vote_url and not is_valid_url(vote_url):
        errors.append(f"vote_url non è un URL https valido: '{vote_url}'")

    return errors


def validate_all(dedications: list) -> bool:
    """Valida tutte le dediche. Restituisce True se tutte passano."""
    import re
    seen_ids = set()
    active_dates = {}
    total_errors = 0

    for ded in dedications:
        ded_id = ded.get('id', '<NESSUN_ID>')
        status = ded.get('status', '')

        if status == 'draft':
            logger.info(f"  ↳ SKIP (draft): {ded_id}")
            continue

        errors = validate_dedication(ded, seen_ids, active_dates)

        if ded.get('id'):
            seen_ids.add(ded['id'])

        if errors:
            total_errors += len(errors)
            logger.error(f"ERRORI in '{ded_id}':")
            for e in errors:
                logger.error(f"   ✗ {e}")
        else:
            logger.info(f"  ✓ OK: {ded_id} [{status}]")

    if total_errors:
        logger.error(f"\n❌ Validazione FALLITA: {total_errors} errori trovati")
        return False

    logger.info(f"\n✅ Validazione OK: {len(dedications)} dediche valide")
    return True


def main():
    parser = argparse.ArgumentParser(description='Valida le dediche DDGPilliSite')
    parser.add_argument('--strict', action='store_true', help='Blocca anche su warning')
    args = parser.parse_args()

    logger.info("=== Validazione dediche DDGPilliSite ===")

    from scripts.utils import load_all_dedications
    dedications = load_all_dedications()
    logger.info(f"Trovate {len(dedications)} dediche in data/dedications/")

    if not dedications:
        logger.warning("Nessuna dedica trovata.")
        sys.exit(0)

    success = validate_all(dedications)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
