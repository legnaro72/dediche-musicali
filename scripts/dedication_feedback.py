"""
Servizio condiviso per salvare feedback persistente sulle dediche.

Questo modulo non dipende da Streamlit: puo essere usato da admin UI,
script CLI, micro API o in futuro da un backend Atlas.
"""
from __future__ import annotations

import base64
import json
import os
from copy import deepcopy
from typing import Any

import requests

from scripts.utils import (
    DATA_DIR,
    find_existing_dedication_path,
    get_rome_now,
    load_all_dedications,
    load_json,
    save_json,
)

REACTION_KEYS = ("down", "like", "heart", "sun")
GITHUB_API = "https://api.github.com"


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


def _github_token() -> str:
    return (
        os.environ.get("DDGPILLI_GITHUB_TOKEN")
        or os.environ.get("GITHUB_PAT")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or ""
    ).strip()


def use_github_backend() -> bool:
    return os.environ.get("DDGPILLI_FEEDBACK_BACKEND", "").strip().lower() == "github"


def _github_repo() -> str:
    repo = os.environ.get("DDGPILLI_GITHUB_REPO") or os.environ.get("GITHUB_REPO") or ""
    repo = repo.strip()
    if not repo:
        raise ValueError("DDGPILLI_GITHUB_REPO mancante, esempio: legnaro72/dediche-musicali.")
    return repo


def _github_branch() -> str:
    return (os.environ.get("DDGPILLI_GITHUB_BRANCH") or os.environ.get("GITHUB_BRANCH") or "main").strip()


def _github_headers() -> dict[str, str]:
    token = _github_token()
    if not token:
        raise ValueError("Token GitHub mancante. Configura DDGPILLI_GITHUB_TOKEN come secret del backend.")
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _github_request(method: str, path: str, **kwargs):
    response = requests.request(
        method,
        f"{GITHUB_API}/repos/{_github_repo()}/{path.lstrip('/')}",
        headers=_github_headers(),
        timeout=25,
        **kwargs,
    )
    if response.status_code >= 400:
        raise ValueError(f"GitHub API error {response.status_code}: {response.text}")
    return response


def _dedication_file_name(dedication: dict) -> str:
    current_path = find_existing_dedication_path(str(dedication.get("id", "")), str(dedication.get("date", "")))
    if current_path:
        return current_path.name
    return f"{dedication.get('id')}.json"


def _github_load_path(repo_path: str) -> tuple[dict, str]:
    response = _github_request("GET", f"contents/{repo_path}", params={"ref": _github_branch()})
    payload = response.json()
    content = base64.b64decode(payload["content"]).decode("utf-8-sig")
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError(f"JSON GitHub non valido: {repo_path}")
    return ensure_feedback_fields(data), payload["sha"]


def _github_load_dedication(dedication_id: str) -> tuple[dict, str, str]:
    dedication_id = (dedication_id or "").strip()
    if not dedication_id:
        raise ValueError("dedication_id obbligatorio.")

    direct_path = f"data/dedications/{dedication_id}.json"
    try:
        dedication, sha = _github_load_path(direct_path)
        return dedication, direct_path, sha
    except Exception:
        pass

    response = _github_request("GET", "contents/data/dedications", params={"ref": _github_branch()})
    for item in response.json():
        if not str(item.get("name", "")).endswith(".json"):
            continue
        dedication, sha = _github_load_path(item["path"])
        if dedication.get("id") == dedication_id:
            return dedication, item["path"], sha

    raise FileNotFoundError(f"Dedica non trovata su GitHub: {dedication_id}")


def _github_save_dedication(dedication: dict, repo_path: str, sha: str, message: str) -> dict:
    encoded = base64.b64encode(
        json.dumps(dedication, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("ascii")
    payload = {
        "message": message,
        "content": encoded,
        "sha": sha,
        "branch": _github_branch(),
    }
    _github_request("PUT", f"contents/{repo_path}", json=payload)
    return dedication


def _load_feedback_target(dedication_id: str) -> tuple[dict, Any, str | None]:
    if use_github_backend():
        dedication, repo_path, sha = _github_load_dedication(dedication_id)
        return dedication, repo_path, sha
    dedication, path = _load_existing_dedication(dedication_id)
    return dedication, path, None


def _save_feedback_target(dedication: dict, target: Any, sha: str | None, message: str) -> dict:
    if use_github_backend():
        if not sha:
            raise ValueError("SHA GitHub mancante per il salvataggio.")
        return _github_save_dedication(dedication, str(target), sha, message)
    if not save_json(dedication, target):
        raise OSError(f"Impossibile salvare {target}")
    return dedication


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
    dedication, _target, _sha = _load_feedback_target(dedication_id)
    return feedback_payload(dedication)


def load_all_feedback() -> dict[str, dict]:
    if use_github_backend():
        response = _github_request("GET", "contents/data/dedications", params={"ref": _github_branch()})
        feedback = {}
        for item in response.json():
            if not str(item.get("name", "")).endswith(".json"):
                continue
            dedication, _sha = _github_load_path(item["path"])
            payload = feedback_payload(dedication)
            if payload["id"]:
                feedback[payload["id"]] = payload
        return feedback

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

    dedication, target, sha = _load_feedback_target(dedication_id)
    dedication["votoPilly"] = vote
    dedication["pensieroPilly"] = str(pensiero_pilly or "").strip()
    dedication["updated_at"] = get_rome_now().isoformat()

    return _save_feedback_target(
        dedication,
        target,
        sha,
        f"Salva voto Pilly {dedication_id}",
    )


def update_reaction(
    dedication_id: str,
    reaction: str | None,
    previous_reaction: str | None = None,
) -> dict:
    """Aggiorna i conteggi reaction per una dedica."""
    reaction = str(reaction or "").strip()
    previous_reaction = str(previous_reaction or "").strip()
    if reaction and reaction not in REACTION_KEYS:
        raise ValueError(f"reaction non valida. Usa una tra: {', '.join(REACTION_KEYS)}")
    if previous_reaction and previous_reaction not in REACTION_KEYS:
        raise ValueError(f"previous_reaction non valida. Usa una tra: {', '.join(REACTION_KEYS)}")
    if not reaction and not previous_reaction:
        raise ValueError("reaction o previous_reaction obbligatoria.")

    dedication, target, sha = _load_feedback_target(dedication_id)
    reactions = normalize_reactions(dedication.get("reactions"))
    if previous_reaction:
        reactions[previous_reaction] = max(0, reactions[previous_reaction] - 1)
    if reaction:
        reactions[reaction] += 1
    dedication["reactions"] = reactions
    dedication["updated_at"] = get_rome_now().isoformat()

    return _save_feedback_target(
        dedication,
        target,
        sha,
        f"Salva reazione Pilly {dedication_id}",
    )
