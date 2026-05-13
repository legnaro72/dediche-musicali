import base64
import datetime
import json
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
DAILY_WORKFLOW_FILE = os.environ.get("DAILY_WORKFLOW_FILE", "daily-publish.yml")
UPLOAD_DIR = "public/images/upload"
VALID_IMAGE_MODES = ("raw", "auto", "upload", "none")
VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VALID_STATUSES = ("draft", "scheduled", "published", "disabled")

SHEET_COLUMNS = [
    "id",
    "date",
    "status",
    "song_title",
    "artist",
    "dedication_title",
    "dedication_text",
    "audio_url",
    "audio_type",
    "vote_url",
    "image_mode",
    "image_source",
    "short_phrase",
    "tags",
    "seo_title",
    "seo_description",
    "image_alt",
]

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
        "ma restano dentro piu' di tante parole.\n"
        f"Oggi ti dedico \"{song_title}\" di {artist}, "
        "perche' certe emozioni meritano di essere ascoltate fino in fondo. 🎵"
    )


def default_short_phrase() -> str:
    return "Alcune emozioni restano anche dopo l'ultima nota."


def get_secret_or_env(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.environ.get(name, default) or "").strip()


def get_github_token() -> str:
    token = (
        get_secret_or_env("GITHUB_TOKEN")
        or get_secret_or_env("GH_TOKEN")
        or get_secret_or_env("GITHUB_PAT")
        or ""
    ).strip()
    if not token:
        raise ValueError(
            "Imposta GITHUB_TOKEN, GH_TOKEN oppure GITHUB_PAT. "
            "Per Pubblica subito servono permessi Contents: write e Actions: write."
        )
    return token


def get_google_credentials(scopes: list[str]) -> Credentials:
    try:
        service_account_info = st.secrets.get("gcp_service_account", None)
    except Exception:
        service_account_info = None

    if service_account_info:
        return Credentials.from_service_account_info(
            dict(service_account_info),
            scopes=scopes,
        )

    service_account_json = get_secret_or_env("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        return Credentials.from_service_account_info(
            json.loads(service_account_json),
            scopes=scopes,
        )

    if SERVICE_ACCOUNT_FILE.exists():
        return Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=scopes,
        )

    raise ValueError(
        "Credenziali Google mancanti. Su Streamlit Cloud configura la tabella "
        "[gcp_service_account] nei secrets."
    )


def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = get_google_credentials(scopes)
    sheet_id = get_secret_or_env("GOOGLE_SHEET_ID", GOOGLE_SHEET_ID)
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID mancante nei secrets o nell'ambiente.")
    client = gspread.authorize(credentials)
    return client.open_by_key(sheet_id).sheet1


def load_sheet_records() -> list[dict]:
    sheet = get_sheet()
    rows = sheet.get_all_records()
    records = []
    for idx, row in enumerate(rows, start=2):
        record = {col: str(row.get(col, "") or "") for col in SHEET_COLUMNS}
        record["_row_number"] = idx
        records.append(record)
    return records


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


def dispatch_daily_publish(date_value: str, force_republish: bool = True) -> None:
    token = get_github_token()
    api_url = (
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/"
        f"{DAILY_WORKFLOW_FILE}/dispatches"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "ref": GITHUB_BRANCH,
        "inputs": {
            "date": date_value,
            "force_republish": "true" if force_republish else "false",
            "dry_run": "false",
        },
    }
    response = requests.post(api_url, headers=headers, json=payload, timeout=20)
    if response.status_code != 204:
        raise ValueError(f"Avvio workflow GitHub Actions fallito: {response.text}")


def make_default_id(date_value: str, song_title: str, artist: str) -> str:
    return f"{date_value}-{slugify(song_title)}-{slugify(artist)}"


def default_form_values() -> dict:
    return {
        "id": "",
        "date": "",
        "status": "scheduled",
        "song_title": "",
        "artist": "",
        "dedication_title": "La dedica del giorno",
        "dedication_text": "",
        "audio_url": "",
        "audio_type": "spotify",
        "vote_url": DEFAULT_VOTE_URL,
        "image_mode": "raw",
        "image_source": "",
        "short_phrase": "",
        "tags": "musica,emozioni,dedica",
        "seo_title": "",
        "seo_description": "",
        "image_alt": "",
    }


def build_row_from_values(values: dict) -> list[str]:
    return [str(values.get(col, "") or "").strip() for col in SHEET_COLUMNS]


def prepare_values(values: dict) -> dict:
    cleaned = {col: str(values.get(col, "") or "").strip() for col in SHEET_COLUMNS}
    cleaned["date"] = normalize_date(cleaned["date"])

    if not cleaned["song_title"]:
        raise ValueError("Inserisci il titolo della canzone.")
    if not cleaned["artist"]:
        raise ValueError("Inserisci l'artista.")
    if not cleaned["audio_url"].startswith("https://open.spotify.com/"):
        raise ValueError("Inserisci un URL Spotify valido.")
    if not cleaned["dedication_text"]:
        raise ValueError("Inserisci o genera dedication_text.")
    if not cleaned["short_phrase"]:
        raise ValueError("Inserisci o genera short_phrase.")
    if cleaned["status"] not in VALID_STATUSES:
        raise ValueError(f"Status non valido. Usa uno tra: {', '.join(VALID_STATUSES)}")
    if cleaned["image_mode"] not in VALID_IMAGE_MODES:
        raise ValueError(f"image_mode non valido. Usa uno tra: {', '.join(VALID_IMAGE_MODES)}")

    if not cleaned["id"]:
        cleaned["id"] = make_default_id(cleaned["date"], cleaned["song_title"], cleaned["artist"])
    if not cleaned["dedication_title"]:
        cleaned["dedication_title"] = "La dedica del giorno"
    if not cleaned["audio_type"]:
        cleaned["audio_type"] = "spotify"
    if not cleaned["vote_url"]:
        cleaned["vote_url"] = DEFAULT_VOTE_URL
    if not cleaned["tags"]:
        cleaned["tags"] = "musica,emozioni,dedica"
    if not cleaned["seo_title"]:
        cleaned["seo_title"] = f"{cleaned['song_title']} - {cleaned['artist']} | {SITE_NAME}"
    if not cleaned["seo_description"]:
        cleaned["seo_description"] = (
            f"Dedica musicale del giorno con \"{cleaned['song_title']}\" "
            f"di {cleaned['artist']}."
        )
    if not cleaned["image_alt"]:
        cleaned["image_alt"] = f"Dedica musicale {cleaned['song_title']} di {cleaned['artist']}"

    return cleaned


def append_to_google_sheet(row: list[str]) -> None:
    sheet = get_sheet()
    sheet.append_row(row, value_input_option="USER_ENTERED")


def update_google_sheet_row(row_number: int, row: list[str]) -> None:
    sheet = get_sheet()
    end_col = chr(ord("A") + len(SHEET_COLUMNS) - 1)
    sheet.update(f"A{row_number}:{end_col}{row_number}", [row], value_input_option="USER_ENTERED")


def add_to_active_text(value: str, prefix: str) -> None:
    target = st.session_state.get(f"{prefix}_active_text_target", "dedication_text")
    key = f"{prefix}_short_phrase" if target == "short_phrase" else f"{prefix}_dedication_text"
    current = st.session_state.get(key, "")
    st.session_state[key] = f"{current}{value}"


def add_custom_to_active_text(prefix: str) -> None:
    value = st.session_state.get(f"{prefix}_custom_emoji", "").strip()
    if value:
        add_to_active_text(value, prefix)


def clear_texts(prefix: str) -> None:
    st.session_state[f"{prefix}_dedication_text"] = ""
    st.session_state[f"{prefix}_short_phrase"] = ""


def generate_preview(prefix: str) -> None:
    song = st.session_state.get(f"{prefix}_song_title", "").strip()
    artist = st.session_state.get(f"{prefix}_artist", "").strip()
    if not song or not artist:
        st.warning("Inserisci prima titolo canzone e artista.")
        return
    st.session_state[f"{prefix}_dedication_text"] = default_dedication_text(song, artist)
    st.session_state[f"{prefix}_short_phrase"] = default_short_phrase()


def set_form_state(prefix: str, values: dict) -> None:
    defaults = default_form_values()
    defaults.update({col: values.get(col, "") for col in SHEET_COLUMNS})
    for col in SHEET_COLUMNS:
        st.session_state[f"{prefix}_{col}"] = defaults[col]


def init_form_state(prefix: str, values: dict | None = None) -> None:
    defaults = default_form_values()
    if values:
        defaults.update({col: values.get(col, "") for col in SHEET_COLUMNS})
    for col, value in defaults.items():
        st.session_state.setdefault(f"{prefix}_{col}", value)
    st.session_state.setdefault(f"{prefix}_active_text_target", "dedication_text")


def collect_form_state(prefix: str) -> dict:
    return {col: st.session_state.get(f"{prefix}_{col}", "") for col in SHEET_COLUMNS}


def render_emoji_picker(prefix: str) -> None:
    st.caption("Clicca prima nel testo o nella frase breve, poi inserisci l'emoji.")
    st.radio(
        "Campo attivo",
        options=("dedication_text", "short_phrase"),
        horizontal=True,
        key=f"{prefix}_active_text_target",
    )

    st.markdown("**Emoji rapide**")
    cols = st.columns(len(QUICK_EMOJIS))
    for col, emoji in zip(cols, QUICK_EMOJIS):
        col.button(
            emoji,
            key=f"{prefix}_quick_{emoji}",
            on_click=add_to_active_text,
            args=(emoji, prefix),
        )

    with st.expander("Emoji estese"):
        for row_start in range(0, len(EXTENDED_EMOJIS), 8):
            row = EXTENDED_EMOJIS[row_start:row_start + 8]
            cols = st.columns(len(row))
            for col, emoji in zip(cols, row):
                col.button(
                    emoji,
                    key=f"{prefix}_extended_{row_start}_{emoji}",
                    on_click=add_to_active_text,
                    args=(emoji, prefix),
                )

    st.text_input("Emoji o testo speciale libero", key=f"{prefix}_custom_emoji")
    st.button(
        "Inserisci nel campo attivo",
        use_container_width=True,
        on_click=add_custom_to_active_text,
        args=(prefix,),
    )


def render_dedication_form(prefix: str, existing_image_source: str = ""):
    st.subheader("Dati principali")
    st.text_input("ID", key=f"{prefix}_id", help="Lascia vuoto per generarne uno automaticamente.")
    st.text_input("Data", placeholder="2026-05-14 oppure 14/05/2026", key=f"{prefix}_date")
    st.selectbox(
        "status",
        VALID_STATUSES,
        index=VALID_STATUSES.index(st.session_state.get(f"{prefix}_status", "scheduled"))
        if st.session_state.get(f"{prefix}_status", "scheduled") in VALID_STATUSES else 1,
        key=f"{prefix}_status",
    )
    st.text_input("Titolo canzone", key=f"{prefix}_song_title")
    st.text_input("Artista", key=f"{prefix}_artist")
    st.text_input("URL Spotify", key=f"{prefix}_audio_url")
    st.text_input("Titolo dedica", key=f"{prefix}_dedication_title")

    st.subheader("Immagine")
    image_mode = st.selectbox(
        "image_mode",
        VALID_IMAGE_MODES,
        index=VALID_IMAGE_MODES.index(st.session_state.get(f"{prefix}_image_mode", "raw"))
        if st.session_state.get(f"{prefix}_image_mode", "raw") in VALID_IMAGE_MODES else 0,
        key=f"{prefix}_image_mode",
    )
    uploaded_file = st.file_uploader(
        "Nuova immagine per raw/upload",
        type=["jpg", "jpeg", "png", "webp"],
        disabled=image_mode not in ("raw", "upload"),
        key=f"{prefix}_uploaded_file",
    )
    st.text_input("image_source", key=f"{prefix}_image_source")
    if existing_image_source and not uploaded_file:
        st.caption(f"Immagine attuale: {existing_image_source}")
    if uploaded_file:
        date_text = st.session_state.get(f"{prefix}_date", "")
        preview_date = normalize_date(date_text) if date_text else "YYYY-MM-DD"
        st.info(f"Verra' caricata come {preview_date}{Path(uploaded_file.name).suffix.lower()}")

    st.subheader("Testi")
    st.text_area(
        "dedication_text",
        key=f"{prefix}_dedication_text",
        height=180,
        placeholder="Genera un'anteprima o scrivi il testo manualmente...",
    )
    st.text_input("short_phrase", key=f"{prefix}_short_phrase")
    st.text_input("tags", key=f"{prefix}_tags")

    with st.expander("SEO e opzioni avanzate"):
        st.text_input("audio_type", key=f"{prefix}_audio_type")
        st.text_input("vote_url", key=f"{prefix}_vote_url")
        st.text_input("seo_title", key=f"{prefix}_seo_title")
        st.text_area("seo_description", key=f"{prefix}_seo_description", height=80)
        st.text_input("image_alt", key=f"{prefix}_image_alt")

    col_preview, col_clear = st.columns(2)
    col_preview.button(
        "Genera anteprima testo",
        use_container_width=True,
        on_click=generate_preview,
        args=(prefix,),
    )
    col_clear.button(
        "Pulisci testi",
        use_container_width=True,
        on_click=clear_texts,
        args=(prefix,),
    )

    render_emoji_picker(prefix)
    return uploaded_file


def save_dedication(prefix: str, uploaded_file, mode: str, row_number: int | None = None) -> dict:
    values = prepare_values(collect_form_state(prefix))
    if uploaded_file is not None:
        with st.spinner("Caricamento immagine su GitHub..."):
            values["image_source"] = upload_image_to_github(uploaded_file, values["date"])

    if values["image_mode"] in ("raw", "upload") and not values["image_source"]:
        raise ValueError(f"Seleziona un'immagine o compila image_source per image_mode={values['image_mode']}.")

    row = build_row_from_values(values)
    if mode == "edit":
        if row_number is None:
            raise ValueError("Riga Google Sheet non trovata per la modifica.")
        with st.spinner("Aggiornamento riga nel Google Sheet..."):
            update_google_sheet_row(row_number, row)
    else:
        with st.spinner("Inserimento nel Google Sheet..."):
            append_to_google_sheet(row)

    set_form_state(prefix, values)
    return values


def save_and_optionally_publish(prefix: str, uploaded_file, mode: str, publish_now: bool,
                                row_number: int | None = None) -> None:
    values = save_dedication(prefix, uploaded_file, mode, row_number=row_number)
    action = "aggiornata" if mode == "edit" else "programmata"
    st.success(f"Dedica {action} per il {values['date']}.")

    if publish_now:
        with st.spinner("Avvio workflow GitHub Actions..."):
            dispatch_daily_publish(values["date"], force_republish=True)
        st.success(
            "Workflow daily-publish avviato. Il sito verra' aggiornato appena GitHub Actions termina."
        )


def render_new_dedication() -> None:
    init_form_state("new")
    st.title("Nuova dedica musicale")
    st.caption("Crea una nuova riga nel Google Sheet e, se vuoi, pubblicala subito.")

    uploaded_file = render_dedication_form("new")

    col_save, col_publish = st.columns(2)
    save_clicked = col_save.button(
        "Salva nel Google Sheet",
        use_container_width=True,
    )
    publish_clicked = col_publish.button(
        "Pubblica subito",
        type="primary",
        use_container_width=True,
    )

    if save_clicked or publish_clicked:
        try:
            save_and_optionally_publish(
                "new",
                uploaded_file,
                mode="new",
                publish_now=publish_clicked,
            )
        except Exception as exc:
            st.error(str(exc))


def format_record_label(record: dict) -> str:
    return (
        f"{record.get('date', '')} - {record.get('song_title', '')} "
        f"({record.get('artist', '')}) [{record.get('status', '')}]"
    )


def render_historical() -> None:
    st.title("Historical")
    st.caption("Legge le dediche dal Google Sheet e aggiorna la riga selezionata.")

    if st.button("Ricarica Google Sheet"):
        st.cache_data.clear()

    try:
        records = load_sheet_records()
    except Exception as exc:
        st.error(str(exc))
        return

    if not records:
        st.info("Nessuna dedica trovata nel Google Sheet.")
        return

    records = sorted(records, key=lambda r: r.get("date", ""), reverse=True)
    options = {format_record_label(record): record for record in records}
    selected_label = st.selectbox("Seleziona dedica", list(options.keys()))
    selected = options[selected_label]

    selected_key = f"{selected.get('_row_number')}-{selected.get('id')}"
    if st.session_state.get("historical_loaded_key") != selected_key:
        set_form_state("hist", selected)
        st.session_state["historical_loaded_key"] = selected_key

    uploaded_file = render_dedication_form("hist", existing_image_source=selected.get("image_source", ""))

    col_save, col_publish = st.columns(2)
    save_clicked = col_save.button(
        "Salva modifiche",
        use_container_width=True,
    )
    publish_clicked = col_publish.button(
        "Pubblica subito",
        type="primary",
        use_container_width=True,
    )

    if save_clicked or publish_clicked:
        try:
            save_and_optionally_publish(
                "hist",
                uploaded_file,
                mode="edit",
                publish_now=publish_clicked,
                row_number=int(selected["_row_number"]),
            )
            st.session_state["historical_loaded_key"] = ""
        except Exception as exc:
            st.error(str(exc))


def main() -> None:
    st.set_page_config(page_title="Dediche musicali", page_icon="🎵", layout="centered")
    tab_new, tab_historical = st.tabs(["Nuova dedica", "Historical"])
    with tab_new:
        render_new_dedication()
    with tab_historical:
        render_historical()


if __name__ == "__main__":
    main()
