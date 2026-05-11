# Backups

Questa cartella è destinata ai backup locali del sito.

I file `.zip` non vengono tracciati da Git (vedi `.gitignore`).

I backup automatici vengono salvati come **artifact di GitHub Actions** e sono scaricabili
dalla sezione Actions del repository GitHub.

## Struttura backup

Ogni backup contiene:
- `data/` — tutti i JSON delle dediche
- `public/images/dedications/` — immagini generate
- `src/` — codice sorgente Astro
- `scripts/` — script Python
- `.github/workflows/` — workflow GitHub Actions
- `package.json`, `astro.config.mjs`, `requirements.txt`, `README.md`
