import re
import datetime
import customtkinter as ctk
from tkinter import messagebox
import gspread
from google.oauth2.service_account import Credentials


GOOGLE_SHEET_ID = "1Cv5fXc9yqp1qkODqL53qZhBFhF_Uha0ucyB4RJO8NQU"
SERVICE_ACCOUNT_FILE = "service_account.json"

DEFAULT_VOTE_URL = "https://docs.google.com/forms/d/17VuesL0BOupyw5M5MNCLs1gq_uqZioVKVkGC8oFfn38/viewform"
SITE_NAME = "DDGPilliSite"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("à", "a").replace("è", "e").replace("é", "e")
    text = text.replace("ì", "i").replace("ò", "o").replace("ù", "u")
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


def build_row(date_value, song_title, artist, spotify_url):
    song_slug = slugify(song_title)
    artist_slug = slugify(artist)

    dedication_id = f"{date_value}-{song_slug}-{artist_slug}"

    dedication_text = (
        f"Ci sono canzoni che arrivano senza fare rumore, "
        f"ma restano dentro più di tante parole.\n"
        f"Oggi ti dedico “{song_title}” di {artist}, "
        f"perché certe emozioni meritano di essere ascoltate fino in fondo. 🎵"
    )

    short_phrase = "Alcune emozioni restano anche dopo l’ultima nota."

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
        "auto",
        "",
        short_phrase,
        tags,
        seo_title,
        seo_description,
        image_alt,
    ]


def append_to_google_sheet(row):
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


def submit():
    try:
        date_value = normalize_date(date_entry.get())
        song_title = song_entry.get().strip()
        artist = artist_entry.get().strip()
        spotify_url = spotify_entry.get().strip()

        if not song_title:
            raise ValueError("Inserisci il titolo della canzone.")

        if not artist:
            raise ValueError("Inserisci l'artista.")

        if not spotify_url.startswith("https://open.spotify.com/"):
            raise ValueError("Inserisci un URL Spotify valido.")

        row = build_row(date_value, song_title, artist, spotify_url)
        append_to_google_sheet(row)

        messagebox.showinfo(
            "Dedica aggiunta",
            f"Dedica programmata correttamente per il {date_value}!",
        )

        date_entry.delete(0, "end")
        song_entry.delete(0, "end")
        artist_entry.delete(0, "end")
        spotify_entry.delete(0, "end")

    except Exception as e:
        messagebox.showerror("Errore", str(e))


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("DDGPilliSite — Aggiungi dedica")
app.geometry("620x520")
app.resizable(False, False)

frame = ctk.CTkFrame(app, corner_radius=24)
frame.pack(padx=32, pady=32, fill="both", expand=True)

title = ctk.CTkLabel(
    frame,
    text="♪ Nuova dedica musicale",
    font=ctk.CTkFont(size=28, weight="bold"),
)
title.pack(pady=(28, 8))

subtitle = ctk.CTkLabel(
    frame,
    text="Compila i dati e programma automaticamente la dedica",
    font=ctk.CTkFont(size=14),
    text_color="#b8b8b8",
)
subtitle.pack(pady=(0, 24))

date_entry = ctk.CTkEntry(
    frame,
    width=480,
    height=44,
    placeholder_text="Data — esempio 2026-05-13 oppure 13/05/2026",
)
date_entry.pack(pady=8)

song_entry = ctk.CTkEntry(
    frame,
    width=480,
    height=44,
    placeholder_text="Titolo canzone",
)
song_entry.pack(pady=8)

artist_entry = ctk.CTkEntry(
    frame,
    width=480,
    height=44,
    placeholder_text="Artista",
)
artist_entry.pack(pady=8)

spotify_entry = ctk.CTkEntry(
    frame,
    width=480,
    height=44,
    placeholder_text="URL Spotify",
)
spotify_entry.pack(pady=8)

button = ctk.CTkButton(
    frame,
    text="Programma dedica",
    width=260,
    height=48,
    corner_radius=18,
    font=ctk.CTkFont(size=16, weight="bold"),
    command=submit,
)
button.pack(pady=28)

footer = ctk.CTkLabel(
    frame,
    text="La dedica verrà aggiunta al Google Sheet con status = scheduled",
    font=ctk.CTkFont(size=12),
    text_color="#888888",
)
footer.pack(pady=(8, 0))

app.mainloop()