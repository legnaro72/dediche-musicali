# Effetto celebrativo della fotografia

Implementato in locale. Nessun push, modifica della configurazione remota o deploy eseguito.
Il file `public/config/site-settings.json` esistente non viene attivato o alterato da questa modifica.

## Configurazione

In Streamlit aprire **Configurazione sito → Effetto celebrativo**:

1. Attivare **Attiva sulla fotografia in homepage**.
2. Inserire il testo (massimo **120 caratteri Unicode**). Accenti, apostrofi e simboli sono contenuto letterale; non viene interpretato HTML.
3. Impostare la durata totale, **3–30 secondi**, predefinita **10**.
4. Usare il pulsante esistente **Salva configurazione sito**.

Per disattivare: spegnere l'interruttore e salvare, oppure svuotare il testo. L'effetto assente o disattivato non crea canvas, observer, timer o cicli di rendering. Restano soltanto i listener di integrazione già caricati dal modulo e la lettura della configurazione preesistente del sito.

Schema nel medesimo JSON:

```json
"celebration": {
  "enabled": true,
  "text": "Pìlli, sei magia!",
  "duration": 10
}
```

Valori mancanti/invalidi: disattivato, testo vuoto, 10 secondi. Le durate numeriche vengono troncate a secondi interi e limitate a 3–30; i valori non numerici tornano a 10. Il testo viene normalizzato negli spazi e limitato a 120 code point sia in Python sia nel frontend. L'attivazione richiede il booleano `true` e testo non vuoto. Il layout conserva le parole normali, spezza quelle molto lunghe per grafemi e dispone il testo su più righe.

## Salvataggio e pubblicazione

La UI usa `normalize_site_settings` e `save_site_settings` nello script esistente. `write_github_json` serializza UTF-8 con `ensure_ascii=False` e scrive **lo stesso** `public/config/site-settings.json` nel repository/branch già configurati.

La **prima installazione del codice richiede una build Astro e pubblicazione**, da eseguire solo dopo revisione. Il workflow esistente `.github/workflows/deploy.yml` esegue `npm ci`, `npm run build` e pubblica `dist` su GitHub Pages quando si invia codice a `main`.

Dopo l'installazione, i valori vengono letti dinamicamente dal caricatore già presente in `BaseLayout.astro`: JSON locale in anteprima; URL configurato/raw GitHub in produzione; controllo ogni circa 15 secondi e al ritorno sulla pagina. Cambiare testo, durata o attivazione **non richiede una nuova build**, anche se il commit del JSON può comunque avviare il workflow GitHub esistente.

Un effetto in corso viene interrotto subito quando viene disattivato. Il testo e la durata modificati dopo l'avvio valgono dal successivo ingresso in Home: il polling non ripete l'animazione. La configurazione può attivarla una prima volta mentre si è già in Home e non è ancora partita.

## Rendering e ciclo di vita

- `PhotoCelebration.astro` è presente soltanto nella foto della Home. Lo stage relativo avvolge l'immagine; il Canvas assoluto è confinato a quello stage e non comprende didascalia, bordi o aloni. `pointer-events:none`, nessuno spostamento di layout.
- Non vengono toccati i transform, lo zoom o le animazioni esistenti; lo stage segue il movimento della cornice. Nessun intervento su `AudioEmbed` o Spotify.
- Ingresso 0–12%; crescita 12–46%; tensione luminosa 46–55%; disgregazione e dissolvenza 55–100%. Tempi proporzionali alla durata totale.
- Le posizioni iniziali dei frammenti sono campionate dai pixel alpha delle lettere, con reservoir sampling. Scintille/scie/coriandoli nascono da quelle posizioni, non da un emettitore generico.
- Scritta bianco-oro con doppio alone; all'esplosione una sola onda morbida di luce illumina la foto e poi svanisce. Frammenti piu grandi, scie estese e scintille con alone precalcolato su un raster di 64×64 pixel. Restano invariati i limiti di particelle; gli aloni sono limitati a 70 sui dispositivi piccoli e 120 sugli altri, senza blur per particella a ogni frame. Nessuno strobo.
- Canvas 2D, massimo 900.000 pixel e densità 1,5; massimo 420 particelle sui dispositivi piccoli/touch, 760 sugli altri; raster di campionamento massimo 720×1000; scie limitate; 30 fps sui dispositivi piccoli e 60 sugli altri.
- Attesa non bloccante di foto, dimensioni, visibilità e chiusura dell'intro audio. Attesa font fino a 2 secondi, poi font di sistema stabile: il campionamento delle lettere resta coerente con il font visualizzato. Nessun suono nuovo.
- Una sola esecuzione per ingresso/ricaricamento, gestita anche con `astro:page-load`, `astro:before-swap` e ritorno dalla back-forward cache. Nessun loop.
- Resize/orientamento ridimensionano il canvas e ricampionano le lettere conservando la fase temporale; la disposizione può cambiare per adattarsi al nuovo spazio.
- A scheda nascosta, RAF sospeso e tempo congelato: la durata è tempo visibile. Alla fine/uscita/disattivazione vengono cancellati RAF, timer, listener del run, observer, raster e particelle.
- `prefers-reduced-motion`: solo testo fermo con comparsa/dissolvenza; zero particelle. Un cambio di preferenza durante l'effetto lo interrompe.
- Errori di foto/font/canvas o JavaScript disattivato lasciano foto e markup Spotify disponibili. Nessuna dipendenza grafica aggiunta.

## File interessati

- `src/components/PhotoCelebration.astro`: overlay isolato.
- `src/scripts/photo-celebration.js`: disegno, particelle, attese, pulizia e integrazione Astro.
- `src/scripts/celebration-config.js`: validazione e impaginazione.
- `src/pages/index.astro`, `src/styles/experience.css`: stage della sola fotografia, senza modificare gli effetti della cornice.
- `scripts/celebration_config.py`, `scripts/aggiungi_dedica_streamlit.py`: validazione, UI e persistenza esistente.
- Test condivisi in `tests/fixtures/celebration-config.json`, `tests/celebration-config.test.mjs`, `tests/test_celebration_config.py`; prove browser in `tests/celebration.browser.cjs`.
- Fallback senza JavaScript e font non disponibile in `tests/celebration-fallback.browser.cjs`; regressione della foto con `tests/home-photo.browser.cjs`.
- Durata massima mobile in `tests/celebration-duration.browser.cjs`.

## Verifiche e riproduzione

```powershell
npm run build
node --test tests/celebration-config.test.mjs
python -m unittest discover -s tests -p test_celebration_config.py
npm run preview -- --host 127.0.0.1 --port 4336
node tests/celebration.browser.cjs
node tests/celebration-fallback.browser.cjs
node tests/celebration-duration.browser.cjs
```

Il test browser richiede Playwright con Chrome e WebKit installati. `NAV_TEST_URL` cambia URL/porta, `NAV_TEST_DEVICE` seleziona `Desktop`, `Android` o `iPhone`; `PLAYWRIGHT_BROWSERS_PATH` può indicare la cache dei browser.

Le prove usano impostazioni simulate in rete locale: non inviano voti, visite o configurazioni al sito reale. Controllano fasi in tempo reale, fine e rimozione canvas, testo lungo/Unicode/HTML letterale, 3/10/30 secondi sui tre profili, resize, movimento ridotto, pausa di visibilità simulata, navigazioni Astro ripetute, disattivazione in corsa e fallback senza Canvas. Registrazioni e fotogrammi sono in `.cache/playwright/celebration/`, anteprima breve `anteprima-12s.webm`.

Limiti: profili mobile emulati, non dispositivi fisici; riproduzione remota/audio Spotify esclusa dai test (verificato embed invariato). L'interfaccia Streamlit non è stata aperta interattivamente nell'ambiente: validazione, inizializzazione delle sessioni precedenti e salvataggio reale sono verificati isolando le funzioni esistenti e simulando soltanto la rete, senza dipendenze cloud. L'aspetto di emoji/font di sistema può variare fra piattaforme.
