"""
sync_from_google_sheet.py — Legge le dediche dal Google Sheet e genera i JSON.

Richiede:
  GOOGLE_SERVICE_ACCOUNT_JSON  (contenuto JSON del service account)
  GOOGLE_SHEET_ID              (ID del foglio Google)

Uso:
    python scripts/sync_from_google_sheet.py
"""
import sys
import os
import json
import argparse
from datetime import datetime

# Carica variabili locali da .env solo in sviluppo.
# In produzione GitHub Actions continuerà a usare i Secrets.
try:
    from dotenv import load_dotenv
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(base_dir, ".env"))
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import (
    setup_logging, save_json, get_dedication_json_path,
    get_italian_day_name, auto_seo_title, auto_seo_description,
    auto_image_alt, get_rome_now, ROME_TZ,
)

logger = setup_logging('sync')

REQUIRED_COLUMNS = [
    'id', 'date', 'status', 'song_title', 'artist',
    'dedication_title', 'dedication_text', 'audio_url', 'audio_type',
]


def get_gspread_client():
    """Crea client gspread da variabile d'ambiente o file."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive',
        ]

        sa_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '')
        if sa_json:
            sa_info = json.loads(sa_json)
            creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        else:
            # Fallback a file locale (sviluppo)
            sa_file = os.path.join(os.path.dirname(__file__), '..', 'service_account.json')
            creds = Credentials.from_service_account_file(sa_file, scopes=scopes)

        return gspread.authorize(creds)

    except Exception as e:
        logger.error(f"Errore autenticazione Google: {e}")
        raise


def sheet_row_to_dict(row: dict, default_vote_url: str) -> dict:
    """Converte una riga del Google Sheet in un dict dedica normalizzato."""
    date_str = row.get('date', '').strip()
    ded_id = row.get('id', '').strip()
    tags_raw = row.get('tags', '')
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []

    vote_url = row.get('vote_url', '').strip() or default_vote_url
    image_mode = row.get('image_mode', 'auto').strip() or 'auto'

    seo_title = row.get('seo_title', '').strip()
    seo_desc = row.get('seo_description', '').strip()
    image_alt = row.get('image_alt', '').strip()

    now_str = get_rome_now().isoformat()

    ded = {
        'id': ded_id,
        'date': date_str,
        'day_name': get_italian_day_name(date_str),
        'status': row.get('status', 'draft').strip(),
        'song_title': row.get('song_title', '').strip(),
        'artist': row.get('artist', '').strip(),
        'dedication_title': row.get('dedication_title', '').strip(),
        'dedication_text': row.get('dedication_text', '').strip(),
        'audio': {
            'url': row.get('audio_url', '').strip(),
            'type': row.get('audio_type', 'other').strip(),
        },
        'vote': {
            'url': vote_url,
        },
        'image': {
            'path': f'/images/dedications/{date_str}.webp',
            'alt': image_alt or auto_image_alt({'song_title': row.get('song_title',''),
                                                 'artist': row.get('artist',''), 'date': date_str}),
            'mode': image_mode,
            'source': row.get('image_source', '').strip(),
        },
        'short_phrase': row.get('short_phrase', '').strip(),
        'tags': tags,
        'seo': {
            'title': seo_title or auto_seo_title({'song_title': row.get('song_title',''),
                                                   'artist': row.get('artist',''), 'date': date_str}),
            'description': seo_desc or auto_seo_description({'dedication_text': row.get('dedication_text','')}),
        },
        'created_at': now_str,
        'updated_at': now_str,
    }
    return ded


def sync(dry_run: bool = False):
    """Sincronizza dal Google Sheet."""
    sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
    if not sheet_id:
        logger.error("GOOGLE_SHEET_ID non configurato")
        sys.exit(1)

    default_vote_url = os.environ.get('DEFAULT_VOTE_URL', '')

    logger.info("Connessione a Google Sheets...")
    gc = get_gspread_client()
    sh = gc.open_by_key(sheet_id)
    ws = sh.get_worksheet(0)

    rows = ws.get_all_records()
    logger.info(f"Trovate {len(rows)} righe nel Google Sheet")

    saved = 0
    skipped = 0
    errors = 0

    for row in rows:
        ded_id = str(row.get('id', '')).strip()
        date_str = str(row.get('date', '')).strip()
        status = str(row.get('status', '')).strip()

        if not ded_id or not date_str:
            logger.warning(f"Riga senza id o date: {row} — saltata")
            skipped += 1
            continue

        if status == 'disabled':
            logger.info(f"  SKIP (disabled): {ded_id}")
            skipped += 1
            continue

        try:
            ded = sheet_row_to_dict(row, default_vote_url)
            if not dry_run:
                path = get_dedication_json_path(date_str)
                if save_json(ded, path):
                    logger.info(f"  ✓ Salvato: {path.name}")
                    saved += 1
                else:
                    logger.error(f"  ✗ Errore salvataggio: {ded_id}")
                    errors += 1
            else:
                logger.info(f"  [DRY RUN] Salverebbe: {date_str}.json")
                saved += 1
        except Exception as e:
            logger.error(f"  ✗ Errore per '{ded_id}': {e}")
            errors += 1

    logger.info(f"\nSync completata: {saved} salvati, {skipped} saltati, {errors} errori")
    return errors == 0


def main():
    parser = argparse.ArgumentParser(description='Sync da Google Sheet')
    parser.add_argument('--dry-run', action='store_true', help='Non scrivere file')
    args = parser.parse_args()

    logger.info("=== Sync da Google Sheet ===")
    ok = sync(dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
