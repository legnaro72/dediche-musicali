import base64
import datetime
import os
import re
from pathlib import Path

import gspread
import requests
import streamlit as st
from google.oauth2.service_account import Credentials

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass


GOOGLE_SHEET_ID = os.environ.get(
    "GOOGLE_SHEET_ID",
    "1Cv5fXc9yqp1qkODqL53qZhBFhF_Uha0ucyB4RJO8NQU",
)
SERVICE_ACCOUNT_FILE = Path(__file__).resolve().parents[1] / "service_account.json"
DEFAULT_VOTE_URL = os.environ.get(
    "DEFAULT_VOTE_URL",
    "https://docs.google.com/forms/d/17VuesL0BOupyw5M5MNCLs1gq_uqZioVKVkGC8oFfn38/viewform",
)
SITE_NAME = os.environ.get("SITE_NAME", "DDGPilliSite")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "legnaro72/dediche-musicali")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
UPLOAD_DIR = "public/images/upload"
VALID_IMAGE_MODES = ("raw", "auto", "upload", "none")
VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

QUICK_EMOJIS = ["🎵", "❤️", "✨", "🌙", "🌹", "😊", "🙏", "🎧"]
EXTENDED_EMOJIS = [
    "🎶", "💙", "💛", "💜", "💫", "🌟", "☀️", "🌻",
    "🔥", "😍", "🥹", "🕊️", "🎤", "💭", "🌈", "🍀",
    "⭐", "💌", "🤍", "🫶", "🌊", "🎹", "🎸", "🪩",
]


def slugify(text: str) -> str:
    text = text.lower().strip()
    replacements = {
        "à": "a", "á": "a", "â": "a", "ã": "a", "ä": "a",
        "è": "e", "é": "e", "ê": "e", "ë": "e",
        "ì": "i", "í": "i", "î": "i", "ï": "i",
        "ò": "o", "ó": "o", "ô": "o", "õ": "o", "ö": "o",
        "ù": "u", "ú": "u", "û": "u", "ü": "u",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def normalize_date(date_text: str) -> str:
    date_text = date_text.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(date_text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    raise ValueError("Formato data non valido. Usa YYYY-MM-DD oppure DD/MM/YYYY.")


def default_dedication_text(song_title: str, artist: str) -> str:
    return (
        "Ci sono canzoni che arrivano senza fare rumore, "
        "ma restano dentro più di tante parole.\n"
        f"Oggi ti dedico “{song_title}” di {artist}, "
        "perché certe emozioni meritano di essere ascoltate fino in fondo. 🎵"
    )


def default_short_phrase() -> str:
    return "Alcune emozioni restano anche dopo l'ultima nota."


def build_row(
    date_value: str,
    song_title: str,
    artist: str,
    spotify_url: str,
    image_mode: str,
    image_source: str,
    dedication_text: str,
    short_phrase: str,
) -> list[str]:
    dedication_id = f"{date_value}-{slugify(song_title)}-{slugify(artist)}"
    tags = "musica,emozioni,dedica"
    seo_title = f"{song_title} – {artist} | {SITE_NAME}"
    seo_description = f"Dedica musicale del giorno con “{song_title}” di {artist}."
    image_alt = f"Dedica musicale {song_title} di {artist}"

    return [
        dedication_id,
        date_value,
        "scheduled",
        song_title,
        artist,
        "La dedica del giorno",
        dedication_text,
        spotify_url,
        "spotify",
        DEFAULT_VOTE_URL,
        image_mode,
        image_source,
        short_phrase,
        tags,
        seo_title,
        seo_description,
        image_alt,
    ]


def get_github_token() -> str:
    token = (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_PAT")
        or ""
    ).strip()
    if not token:
        raise ValueError(
            "Per caricare immagini su GitHub imposta GITHUB_TOKEN, GH_TOKEN "
            "oppure GITHUB_PAT con permesso Contents: write."
        )
    return token


def upload_image_to_github(uploaded_file, date_value: str) -> str:
    original_name = uploaded_file.name or ""
    ext = Path(original_name).suffix.lower()
    if ext not in VALID_IMAGE_EXTS:
        raise ValueError("Formato immagine non supportato. Usa JPG, JPEG, PNG oppure WEBP.")

    upload_name = f"{date_value}{ext}"
    repo_path = f"{UPLOAD_DIR}/{upload_name}"
    token = get_github_token()
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    sha = None
    existing = requests.get(
        api_url,
        headers=headers,
        params={"ref": GITHUB_BRANCH},
        timeout=20,
    )
    if existing.status_code == 200:
        sha = existing.json().get("sha")
    elif existing.status_code != 404:
        raise ValueError(f"Verifica file GitHub fallita: {existing.text}")

    content_b64 = base64.b64encode(uploaded_file.getvalue()).decode("ascii")
    payload = {
        "message": f"Upload immagine dedica {date_value}",
        "content": content_b64,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    response = requests.put(api_url, headers=headers, json=payload, timeout=30)
    if response.status_code not in (200, 201):
        raise ValueError(f"Upload GitHub fallito: {response.text}")

    return repo_path


def append_to_google_sheet(row: list[str]) -> None:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=scopes,
    )
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
    sheet.append_row(row, value_input_option="USER_ENTERED")


def add_to_active_text(value: str) -> None:
    target = st.session_state.get("active_text_target", "dedication_text")
    key = "short_phrase" if target == "short_phrase" else "dedication_text"
    current = st.session_state.get(key, "")
    st.session_state[key] = f"{current}{value}"


def render_emoji_picker() -> None:
    st.caption("Clicca prima nel testo o nella frase breve, poi inserisci l'emoji.")
    st.radio(
        "Campo attivo",
        options=("dedication_text", "short_phrase"),
        horizontal=True,
        key="active_text_target",
    )

    st.markdown("**Emoji rapide**")
    cols = st.columns(len(QUICK_EMOJIS))
    for col, emoji in zip(cols, QUICK_EMOJIS):
        if col.button(emoji, key=f"quick_{emoji}"):
            add_to_active_text(emoji)

    with st.expander("Emoji estese"):
        for row_start in range(0, len(EXTENDED_EMOJIS), 8):
            row = EXTENDED_EMOJIS[row_start:row_start + 8]
            cols = st.columns(len(row))
            for col, emoji in zip(cols, row):
                if col.button(emoji, key=f"extended_{row_start}_{emoji}"):
                    add_to_active_text(emoji)

    custom = st.text_input("Emoji o testo speciale libero", key="custom_emoji")
    if st.button("Inserisci nel campo attivo", use_container_width=True):
        if custom.strip():
            add_to_active_text(custom.strip())


def init_state() -> None:
    st.session_state.setdefault("date_text", "")
    st.session_state.setdefault("song_title", "")
    st.session_state.setdefault("artist", "")
    st.session_state.setdefault("spotify_url", "")
    st.session_state.setdefault("image_mode", "raw")
    st.session_state.setdefault("dedication_text", "")
    st.session_state.setdefault("short_phrase", "")
    st.session_state.setdefault("active_text_target", "dedication_text")


def generate_preview() -> None:
    song = st.session_state.get("song_title", "").strip()
    artist = st.session_state.get("artist", "").strip()
    if not song or not artist:
        st.warning("Inserisci prima titolo canzone e artista.")
        return
    st.session_state["dedication_text"] = default_dedication_text(song, artist)
    st.session_state["short_phrase"] = default_short_phrase()


def main() -> None:
    st.set_page_config(page_title="Nuova dedica musicale", page_icon="🎵", layout="centered")
    init_state()

    st.title("🎵 Nuova dedica musicale")
    st.caption("Inserisci una dedica programmata nel Google Sheet e, se serve, carica l'immagine su GitHub.")

    st.subheader("Dati principali")
    date_text = st.text_input(
        "Data",
        placeholder="2026-05-14 oppure 14/05/2026",
        key="date_text",
    )
    song_title = st.text_input("Titolo canzone", key="song_title")
    artist = st.text_input("Artista", key="artist")
    spotify_url = st.text_input("URL Spotify", key="spotify_url")

    st.subheader("Immagine")
    image_mode = st.selectbox(
        "image_mode",
        VALID_IMAGE_MODES,
        index=VALID_IMAGE_MODES.index(st.session_state.get("image_mode", "raw")),
        key="image_mode",
    )
    uploaded_file = st.file_uploader(
        "Immagine per raw/upload",
        type=["jpg", "jpeg", "png", "webp"],
        disabled=image_mode not in ("raw", "upload"),
    )
    if uploaded_file:
        preview_date = normalize_date(date_text) if date_text else "YYYY-MM-DD"
        st.info(f"Verrà caricata come {preview_date}{Path(uploaded_file.name).suffix.lower()}")

    st.subheader("Testi")
    st.text_area(
        "dedication_text",
        key="dedication_text",
        height=180,
        placeholder="Genera un'anteprima o scrivi il testo manualmente...",
    )
    st.text_input("short_phrase", key="short_phrase")

    col_preview, col_clear = st.columns(2)
    if col_preview.button("Genera anteprima testo", use_container_width=True):
        generate_preview()
        st.rerun()
    if col_clear.button("Pulisci testi", use_container_width=True):
        st.session_state["dedication_text"] = ""
        st.session_state["short_phrase"] = ""
        st.rerun()

    render_emoji_picker()

    submitted = st.button(
        "Carica immagine e inserisci nel Google Sheet",
        type="primary",
        use_container_width=True,
    )

    if submitted:
        try:
            date_value = normalize_date(date_text)
            song_title = song_title.strip()
            artist = artist.strip()
            spotify_url = spotify_url.strip()
            dedication_text = st.session_state.get("dedication_text", "").strip()
            short_phrase = st.session_state.get("short_phrase", "").strip()

            if not song_title:
                raise ValueError("Inserisci il titolo della canzone.")
            if not artist:
                raise ValueError("Inserisci l'artista.")
            if not spotify_url.startswith("https://open.spotify.com/"):
                raise ValueError("Inserisci un URL Spotify valido.")
            if not dedication_text:
                raise ValueError("Inserisci o genera dedication_text.")
            if not short_phrase:
                raise ValueError("Inserisci o genera short_phrase.")
            if image_mode in ("raw", "upload") and uploaded_file is None:
                raise ValueError(f"Seleziona un'immagine per image_mode={image_mode}.")

            image_source = ""
            if image_mode in ("raw", "upload"):
                with st.spinner("Caricamento immagine su GitHub..."):
                    image_source = upload_image_to_github(uploaded_file, date_value)

            row = build_row(
                date_value,
                song_title,
                artist,
                spotify_url,
                image_mode,
                image_source,
                dedication_text,
                short_phrase,
            )

            with st.spinner("Inserimento nel Google Sheet..."):
                append_to_google_sheet(row)

            st.success(f"Dedica programmata per il {date_value}.")
            if image_source:
                st.code(image_source)
        except Exception as exc:
            st.error(str(exc))


if __name__ == "__main__":
    main()
