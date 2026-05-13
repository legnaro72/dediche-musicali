# ♪ DDGPilliSite

> Sito di dediche musicali giornaliere — gratuito, automatico, moderno.

**Stack:** Astro · GitHub Pages · GitHub Actions · Python · Google Sheet

---

## Indice
1. [Descrizione](#-descrizione)
2. [Architettura](#-architettura)
3. [Prerequisiti](#-prerequisiti)
4. [Setup locale](#-setup-locale)
5. [Configurazione Google Sheet](#-configurazione-google-sheet)
6. [Configurazione GitHub Secrets](#-configurazione-github-secrets)
7. [Configurazione GitHub Pages](#-configurazione-github-pages)
8. [Deploy](#-deploy)
9. [Pubblicazione automatica](#-pubblicazione-automatica)
10. [Pubblicazione manuale](#-pubblicazione-manuale)
11. [Backup](#-backup)
12. [Restore](#-restore)
13. [Aggiungere nuove dediche](#-aggiungere-nuove-dediche)
14. [Correggere dediche pubblicate](#-correggere-dediche-pubblicate)
15. [Struttura repository](#-struttura-repository)
16. [Campi Google Sheet](#-campi-google-sheet)
17. [Troubleshooting](#-troubleshooting)
18. [Futura app Streamlit](#-futura-app-streamlit)

---

## 📖 Descrizione

DDGPilliSite pubblica automaticamente una nuova dedica musicale ogni giorno.
L'utente inserisce le dediche nel Google Sheet con settimane di anticipo e il sito
fa tutto il resto: legge i dati, genera le immagini, aggiorna il sito su GitHub Pages.

**Funzionalità:**
- Homepage con dedica del giorno
- Pagina archivio con ricerca e filtri
- Pagina dettaglio per ogni dedica
- Immagini generate automaticamente con Python/Pillow
- Embed audio (Spotify, YouTube, SoundCloud, MP3)
- Pulsante "Ascolta" e pulsante "Votami" (Google Form)
- SEO automatico: title, description, OpenGraph, Twitter card, sitemap
- Dark mode premium con glassmorphism e animazioni
- Backup automatici come artifact GitHub Actions
- **Costo: 0 €/mese**

---

## 🏗 Architettura

```
Google Sheet
    ↓ (sync_from_google_sheet.py)
JSON locali (data/dedications/)
    ↓ (validate_dedications.py)
Validazione dati
    ↓ (generate_image.py)
Immagini WebP (public/images/dedications/)
    ↓ (publish_daily.py)
Stato aggiornato → published
    ↓ (astro build)
Sito statico (dist/)
    ↓ (GitHub Actions)
GitHub Pages → sito pubblico
```

---

## ✅ Prerequisiti

- Account GitHub
- Repository GitHub (consigliato: `dediche-musicali`)
- Google Sheet configurato (vedi sezione sotto)
- Google Form già creato (per il pulsante "Votami")
- Python 3.11+ (per sviluppo locale)
- Node.js 20+ e npm (per sviluppo locale)

---

## 💻 Setup locale

### 1. Clona il repository

```bash
git clone https://github.com/USERNAME/dediche-musicali.git
cd dediche-musicali
```

### 2. Installa dipendenze frontend

```bash
npm install
```

### 3. Avvia server di sviluppo

```bash
npm run dev
# Il sito sarà disponibile su http://localhost:4321
```

### 4. Configura ambiente Python

```bash
# Linux / macOS
python -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt
```

### 5. Crea file .env locale (opzionale, solo sviluppo)

```env
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_SHEET_ID=1aBcDeFgHiJkLmNoPqRsTuVwXy
DEFAULT_VOTE_URL=https://forms.google.com/...
SITE_NAME=DDGPilliSite
SITE_URL=https://username.github.io/dediche-musicali
```

### 6. Comandi Python disponibili

```bash
# Validazione dati
python scripts/validate_dedications.py

# Sync da Google Sheet
python scripts/sync_from_google_sheet.py

# Pubblicazione manuale
python scripts/publish_daily.py --date 2026-05-12

# Dry run (simula senza scrivere)
python scripts/publish_daily.py --date 2026-05-12 --dry-run

# Genera immagini per una data
python scripts/generate_image.py --date 2026-05-12

# Genera immagini per tutte le dediche
python scripts/generate_image.py --all

# Crea backup locale
python scripts/backup_site.py
```

### 7. Build produzione

```bash
npm run build
npm run preview
```

---

## 📊 Configurazione Google Sheet

### Crea il foglio

1. Apri [Google Sheets](https://sheets.google.com) e crea un nuovo foglio.
2. Nella prima riga inserisci **esattamente** queste intestazioni (case-sensitive):

```
id | date | status | song_title | artist | dedication_title | dedication_text | audio_url | audio_type | vote_url | image_mode | image_source | short_phrase | tags | seo_title | seo_description | image_alt
```

### Crea Service Account

1. Vai su [Google Cloud Console](https://console.cloud.google.com)
2. Crea un nuovo progetto (o usa uno esistente)
3. Abilita **Google Sheets API** e **Google Drive API**
4. Crea credenziali → **Service Account**
5. Scarica il file JSON delle credenziali
6. Copia il contenuto del JSON — ti servirà come secret `GOOGLE_SERVICE_ACCOUNT_JSON`

### Condividi il foglio

1. Apri il Google Sheet
2. Clicca "Condividi"
3. Aggiungi l'email del service account (es. `nome@progetto.iam.gserviceaccount.com`)
4. Imposta permesso: **Lettore** (o Editor se vuoi che gli script aggiornino gli stati)

---

## 🔐 Configurazione GitHub Secrets

Da GitHub: `Repository → Settings → Secrets and variables → Actions → New repository secret`

| Secret | Valore |
|--------|--------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Contenuto JSON del service account |
| `GOOGLE_SHEET_ID` | ID del Google Sheet (dalla URL) |
| `DEFAULT_VOTE_URL` | URL del Google Form di voto |
| `SITE_NAME` | Nome del sito (es. `DDGPilliSite`) |
| `SITE_URL` | URL completo (es. `https://username.github.io/dediche-musicali`) |

> `GITHUB_TOKEN` è fornito automaticamente da GitHub Actions.

---

## 🌐 Configurazione GitHub Pages

### 1. Modifica astro.config.mjs

```js
export default defineConfig({
  site: 'https://TUO_USERNAME.github.io',
  base: '/NOME_REPOSITORY',
  // ...
});
```

### 2. Abilita GitHub Pages

Da GitHub: `Repository → Settings → Pages`
- **Source:** GitHub Actions

### 3. Imposta permessi workflow

Da GitHub: `Repository → Settings → Actions → General`
- **Workflow permissions:** Read and write permissions ✓
- **Allow GitHub Actions to create and approve pull requests** ✓

---

## 🚀 Deploy

### Primo deploy

```bash
npm install
npm run build
git add .
git commit -m "🚀 Setup iniziale DDGPilliSite"
git push origin main
```

Il workflow `deploy.yml` si attiverà automaticamente e pubblicherà il sito.

### PWA, HTTPS e installazione

La Progressive Web App richiede HTTPS con certificato valido. GitHub Pages lo abilita automaticamente quando il dominio è configurato correttamente.

File principali:
- `public/manifest.json` configura installazione, modalità standalone, colori, icone e shortcut.
- `public/sw.js` gestisce cache base, asset statici e navigazione offline best-effort.
- `public/icons/` contiene icone Android/Desktop, maskable icon e asset Apple.
- `public/pwa-config.json` contiene le opzioni modificabili dell'esperienza app.

Configurazione audio:

```json
{
  "backgroundMusic": "/dediche-musicali/background-music/main.mp3",
  "audioDefaultEnabled": true,
  "audioVolume": 0.3
}
```

Per aggiornare la musica:
1. Carica un MP3 leggero in `public/background-music/`.
2. Aggiorna `backgroundMusic` in `public/pwa-config.json`.
3. Regola `audioVolume` tra `0` e `1`.
4. Imposta `audioDefaultEnabled` a `false` se non vuoi tentare l'avvio automatico.

Nota iPhone/Safari: iOS può bloccare l'autoplay audio finché l'utente non interagisce con la pagina. Il sito tenta l'avvio automatico, poi usa il primo tap o tasto premuto come sblocco non invasivo e mantiene la preferenza in `localStorage`.

### Verifica

Il sito sarà disponibile su:
```
https://TUO_USERNAME.github.io/NOME_REPOSITORY/
```

---

## ⏰ Pubblicazione automatica

Il workflow `daily-publish.yml` si esegue automaticamente ogni giorno alle **06:10 ora italiana**.

Flusso automatico:
1. Legge il Google Sheet
2. Trova la dedica del giorno (status = `scheduled`, date = oggi)
3. Valida i dati
4. Genera le immagini
5. Aggiorna lo status a `published`
6. Fa il build di Astro
7. Pubblica su GitHub Pages
8. Fa commit dei nuovi file

Se non esiste una dedica per oggi, il sito resta invariato (nessun errore).

---

## 🔧 Pubblicazione manuale

Da GitHub: `Actions → 🎵 Pubblicazione Giornaliera → Run workflow`

| Input | Descrizione |
|-------|-------------|
| `date` | Data da pubblicare (es. `2026-05-12`). Vuoto = oggi |
| `force_republish` | `true` per forzare anche se già pubblicata |
| `dry_run` | `true` per simulare senza modifiche reali |

---

## 💾 Backup

### Backup automatico

Il workflow `backup.yml` si esegue ogni giorno alle **06:30 ora italiana**.
Il backup viene salvato come **artifact GitHub Actions** (scaricabile per 30 giorni).

Per scaricarlo:
`GitHub → Actions → 💾 Backup Automatico → ultimo run → Artifacts → backup-XXXXX`

### Backup manuale locale

```bash
python scripts/backup_site.py
# Crea: backups/backup-YYYY-MM-DD.zip
```

### Cosa contiene il backup

```
data/                     ← tutti i JSON delle dediche
public/images/dedications/ ← immagini generate
src/                      ← codice sorgente Astro
scripts/                  ← script Python
.github/workflows/        ← workflow GitHub Actions
package.json
astro.config.mjs
requirements.txt
README.md
```

---

## 🔄 Restore

### Livello 1 — Rollback Git

```bash
# Visualizza la storia dei commit
git log --oneline -20

# Ripristina a un commit precedente (senza perdere la storia)
git revert <COMMIT_SHA>
git push origin main
```

### Livello 2 — Restore da artifact

1. Scarica il backup zip da GitHub Actions
2. Estrai il contenuto
3. Copia i file nella directory del progetto
4. Fai commit e push:

```bash
git add .
git commit -m "♻️ Restore da backup YYYY-MM-DD"
git push origin main
```

### Ripristino singola dedica

```bash
# Ripristina il JSON da un backup
cp backup-extracted/data/dedications/2026-05-12.json data/dedications/
git add data/dedications/2026-05-12.json
git commit -m "♻️ Restore dedica 2026-05-12"
git push origin main
```

### Ripristino singola immagine

```bash
cp backup-extracted/public/images/dedications/2026-05-12.webp public/images/dedications/
git add public/images/dedications/2026-05-12.webp
git commit -m "♻️ Restore immagine 2026-05-12"
git push origin main
```

---

## ➕ Aggiungere nuove dediche

1. Apri il Google Sheet
2. Aggiungi una nuova riga con i dati della dedica
3. Imposta `status = scheduled` e la data futura desiderata
4. Salva il foglio
5. Il giorno indicato, GitHub Actions pubblicherà automaticamente la dedica

**Non è necessario toccare il codice.**

---

## ✏️ Correggere dediche pubblicate

### Metodo principale (Google Sheet)

1. Modifica la riga nel Google Sheet
2. Da GitHub: `Actions → 🎵 Pubblicazione Giornaliera → Run workflow`
3. Inserisci la data da correggere e seleziona `force_republish = true`

### Metodo emergenza (JSON diretto)

> ⚠️ Usare solo in caso di emergenza. Il flusso principale è Google Sheet → Actions.

```bash
# Modifica direttamente il JSON
nano data/dedications/2026-05-12.json

# Commit e push
git add data/dedications/2026-05-12.json
git commit -m "🔧 Correzione dedica 2026-05-12"
git push origin main
```

---

## 📁 Struttura repository

```
/
├── .github/
│   └── workflows/
│       ├── deploy.yml           ← Deploy su push a main
│       ├── daily-publish.yml    ← Pubblicazione giornaliera automatica
│       └── backup.yml           ← Backup automatico
│
├── data/
│   └── dedications/
│       └── YYYY-MM-DD.json     ← Un file per ogni dedica
│
├── public/
│   ├── images/
│   │   └── dedications/
│   │       ├── YYYY-MM-DD.webp      ← Immagine verticale (1080×1350)
│   │       └── YYYY-MM-DD-og.webp   ← Immagine OpenGraph (1200×630)
│   ├── favicon/
│   │   └── favicon.svg
│   └── robots.txt
│
├── scripts/
│   ├── utils.py                ← Funzioni condivise
│   ├── sync_from_google_sheet.py
│   ├── validate_dedications.py
│   ├── generate_image.py
│   ├── publish_daily.py
│   └── backup_site.py
│
├── src/
│   ├── components/
│   │   ├── AudioEmbed.astro    ← Embed audio (Spotify/YouTube/SoundCloud)
│   │   └── DedicationCard.astro ← Card per l'archivio
│   ├── layouts/
│   │   └── BaseLayout.astro   ← Layout base con SEO e navbar
│   ├── pages/
│   │   ├── index.astro         ← Homepage
│   │   ├── archive/
│   │   │   └── index.astro    ← Archivio con filtri
│   │   └── dediche/
│   │       └── [id].astro     ← Pagina singola dedica
│   └── styles/
│       └── global.css          ← Design system
│
├── backups/
│   └── README.md
│
├── astro.config.mjs            ← ⚠️ Modifica con il tuo USERNAME e REPO
├── package.json
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 📋 Campi Google Sheet

| Campo | Obbligatorio | Descrizione |
|-------|:---:|-------------|
| `id` | ✅ | Identificativo univoco. Formato: `YYYY-MM-DD-nome-canzone`. Solo lettere minuscole, numeri, trattini. |
| `date` | ✅ | Data pubblicazione. Formato: `YYYY-MM-DD`. Fuso orario: Europe/Rome. |
| `status` | ✅ | `draft` / `scheduled` / `published` / `disabled` |
| `song_title` | ✅ | Titolo della canzone |
| `artist` | ✅ | Nome dell'artista |
| `dedication_title` | ✅ | Titolo della dedica (es. "La dedica del giorno") |
| `dedication_text` | ✅ | Testo completo. Supporta multilinea, emoji, accenti. |
| `audio_url` | ✅ | Link audio (Spotify, YouTube, SoundCloud, MP3, ecc.). Deve iniziare con `https://` |
| `audio_type` | ✅ | `spotify` / `youtube` / `soundcloud` / `mp3` / `cloud` / `other` |
| `vote_url` | ⚪ | Link Google Form. Se vuoto, usa `DEFAULT_VOTE_URL` dai secrets. |
| `image_mode` | ⚪ | `auto` (genera) / `upload` (manuale) / `none` (placeholder). Default: `auto` |
| `image_source` | ⚪ | Percorso immagine manuale. Solo se `image_mode = upload` |
| `short_phrase` | ⚪ | Frase breve per l'immagine generata |
| `tags` | ⚪ | Tag separati da virgola (es. `amore,estate,ricordi`) |
| `seo_title` | ⚪ | Titolo SEO. Auto-generato se vuoto. |
| `seo_description` | ⚪ | Descrizione SEO. Auto-generata se vuota. |
| `image_alt` | ⚪ | Testo alternativo immagine. Auto-generato se vuoto. |

---

## 🔧 Troubleshooting

### Il workflow fallisce con errore di validazione
- Controlla i log di GitHub Actions
- Verifica che tutti i campi obbligatori siano compilati nel Google Sheet
- Assicurati che `audio_url` inizi con `https://`
- Verifica che non ci siano due dediche con la stessa data

### Il sito non si aggiorna
- Controlla che `status = scheduled` (non `draft`)
- Verifica che la data sia corretta nel formato `YYYY-MM-DD`
- Controlla che GitHub Pages sia configurato su "Source: GitHub Actions"
- Prova un rilancio manuale da Actions

### Errore autenticazione Google Sheet
- Verifica che `GOOGLE_SERVICE_ACCOUNT_JSON` sia corretto (JSON valido)
- Verifica che il Google Sheet sia condiviso con l'email del service account
- Controlla che le API (Sheets + Drive) siano abilitate nel progetto GCloud

### Le immagini non vengono generate
- Le immagini usano Pillow + font Montserrat (scaricato automaticamente)
- Se il download del font fallisce in CI, usa font di sistema
- Verifica che la cartella `public/images/dedications/` esista o venga creata

### Il sito mostra "Nessuna dedica oggi"
- La homepage mostra solo dediche con `status = published` e `date <= oggi`
- Verifica che la dedica sia stata pubblicata correttamente
- Controlla che la data non sia nel futuro

---

## 🚀 Futura app Streamlit

È prevista una futura interfaccia Streamlit per gestire le dediche via GUI.

**Funzioni pianificate:**
- Creare / modificare / disabilitare dediche
- Caricare immagini manualmente
- Generare preview dell'immagine
- Validare i dati prima del salvataggio
- Aggiornare il Google Sheet
- Lanciare GitHub Actions
- Vedere lo stato dell'ultima pubblicazione
- Scaricare / ripristinare backup

**Sicurezza:** I token GitHub e le credenziali Google devono stare in variabili ambiente, mai nel codice.

**Deployment Streamlit:** Streamlit Community Cloud (gratuito) o esecuzione locale.

---

*DDGPilliSite — fatto con ♪ e Python*
