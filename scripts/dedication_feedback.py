"""
Servizio condiviso per salvare feedback persistente sulle dediche.

Questo modulo non dipende da Streamlit: puo essere usato da admin UI,
script CLI, micro API o in futuro da un backend Atlas.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from scripts.utils import (
    find_existing_dedication_path,
    get_rome_now,
    load_all_dedications,
    load_json,
    save_json,
)

REACTION_KEYS = ("down", "like", "heart", "sun")


def default_reactions() -> dict[str, int]:
    return {key: 0 for key in REACTION_KEYS}


def normalize_reactions(value: Any) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    normalized = default_reactions()
    for key in REACTION_KEYS:
        try:
            normalized[key] = max(0, int(source.get(key, 0) or 0))
        except (TypeError, ValueError):
            normalized[key] = 0
    return normalized


def ensure_feedback_fields(dedication: dict) -> dict:
    """Aggiunge i campi feedback standard senza perdere valori esistenti."""
    updated = deepcopy(dedication)
    updated.setdefault("votoPilly", None)
    updated.setdefault("pensieroPilly", "")
    updated["reactions"] = normalize_reactions(updated.get("reactions"))
    return updated


def merge_existing_feedback(target: dict, existing: dict | None) -> dict:
    """Preserva il feedback locale quando una sync rigenera la dedica."""
    updated = ensure_feedback_fields(target)
    if not existing:
        return updated

    existing = ensure_feedback_fields(existing)
    for key in ("votoPilly", "pensieroPilly", "reactions"):
        if key in existing:
            updated[key] = existing[key]
    return updated


def _load_existing_dedication(dedication_id: str) -> tuple[dict, Any]:
    dedication_id = (dedication_id or "").strip()
    if not dedication_id:
        raise ValueError("dedication_id obbligatorio.")

    path = find_existing_dedication_path(dedication_id)
    if not path:
        raise FileNotFoundError(f"Dedica non trovata: {dedication_id}")

    dedication = load_json(path)
    if not isinstance(dedication, dict):
        raise ValueError(f"JSON dedica non valido: {path}")
    return ensure_feedback_fields(dedication), path


def feedback_payload(dedication: dict) -> dict:
    dedication = ensure_feedback_fields(dedication)
    return {
        "id": dedication.get("id", ""),
        "date": dedication.get("date", ""),
        "title": dedication.get("song_title", ""),
        "artist": dedication.get("artist", ""),
        "votoPilly": dedication.get("votoPilly"),
        "pensieroPilly": dedication.get("pensieroPilly", ""),
        "reactions": normalize_reactions(dedication.get("reactions")),
        "updated_at": dedication.get("updated_at", ""),
    }


def load_feedback(dedication_id: str) -> dict:
    dedication, _path = _load_existing_dedication(dedication_id)
    return feedback_payload(dedication)


def load_all_feedback() -> dict[str, dict]:
    feedback = {}
    for dedication in load_all_dedications():
        if not isinstance(dedication, dict):
            continue
        payload = feedback_payload(dedication)
        if payload["id"]:
            feedback[payload["id"]] = payload
    return feedback


def update_vote(dedication_id: str, voto_pilly: int, pensiero_pilly: str = "") -> dict:
    """Aggiorna voto e pensiero di Pilly sul JSON della dedica."""
    try:
        vote = int(voto_pilly)
    except (TypeError, ValueError) as exc:
        raise ValueError("votoPilly deve essere un numero intero da 1 a 10.") from exc
    if vote < 1 or vote > 10:
        raise ValueError("votoPilly deve essere compreso tra 1 e 10.")

    dedication, path = _load_existing_dedication(dedication_id)
    dedication["votoPilly"] = vote
    dedication["pensieroPilly"] = str(pensiero_pilly or "").strip()
    dedication["updated_at"] = get_rome_now().isoformat()

    if not save_json(dedication, path):
        raise OSError(f"Impossibile salvare {path}")
    return dedication


def update_reaction(
    dedication_id: str,
    reaction: str,
    previous_reaction: str | None = None,
) -> dict:
    """Aggiorna i conteggi reaction per una dedica."""
    if reaction not in REACTION_KEYS:
        raise ValueError(f"reaction non valida. Usa una tra: {', '.join(REACTION_KEYS)}")
    if previous_reaction and previous_reaction not in REACTION_KEYS:
        raise ValueError(f"previous_reaction non valida. Usa una tra: {', '.join(REACTION_KEYS)}")

    dedication, path = _load_existing_dedication(dedication_id)
    reactions = normalize_reactions(dedication.get("reactions"))
    if previous_reaction and previous_reaction != reaction:
        reactions[previous_reaction] = max(0, reactions[previous_reaction] - 1)
    reactions[reaction] += 1
    dedication["reactions"] = reactions
    dedication["updated_at"] = get_rome_now().isoformat()

    if not save_json(dedication, path):
        raise OSError(f"Impossibile salvare {path}")
    return dedication
