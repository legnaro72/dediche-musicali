# Verifica navigazione mobile

Il menu prima collegava il `click` direttamente al pulsante della prima pagina.
Le View Transitions di Astro sostituiscono quel nodo, mentre il flag globale
impediva di inizializzare quello nuovo. Il clone aveva anche un listener delegato
al documento, assente nel sito principale.

`src/scripts/navigation.js` ora è un modulo Astro eseguito una volta, con eventi
delegati che risolvono gli elementi della pagina corrente. Il pulsante usa solo
`click` (touch, mouse e tastiera); `pointerdown` gestisce esclusivamente la chiusura
esterna, anche quando Safari non genera un click sul contenuto non interattivo.
Lo stato ARIA viene aggiornato insieme al menu. Cambio pagina, cronologia,
ripristino della pagina e resize chiudono il pannello; lo scroll aggiorna la
navbar corrente.

Il manifest pubblico consente entrambi gli orientamenti (`orientation: any`).
Il menu compatto rimane disponibile fino a 1024 px sui dispositivi touch e il
pannello può scorrere su schermi bassi. Il manifest del pannello amministrativo
Streamlit è separato e non è coinvolto.

## Test ripetibile

Collaudo del 20 settembre 2026: build di 64 pagine riuscita; suite completa
superata su Chrome/Pixel 7 e WebKit/iPhone 13 contro la build di produzione locale,
con animazioni abilitate. Verificato visivamente anche il menu in landscape.

Installare le dipendenze del progetto e rendere disponibile `playwright` a Node
(installazione locale senza salvataggio oppure `NODE_PATH` del runtime di test).
Occorrono Chrome e il browser WebKit installato da Playwright.

1. `npm run build`
2. `npm run preview -- --host 127.0.0.1 --port 4332`
3. Impostare `NAV_TEST_URL=http://127.0.0.1:4332/dediche-musicali/`.
4. `node tests/navigation.browser.cjs`

Il test esegue Chrome/Pixel 7 e WebKit/iPhone 13 con touch. Verifica due giri
Home → Archivio → Statistiche → Link utili → Home, cronologia indietro/avanti,
accessi diretti, dettaglio dedica, tap ripetuti, tastiera, chiusura esterna,
scroll, landscape 844×390 e larghezza 320 px. Un marcatore JS verifica che i
passaggi avvengano tramite Astro, senza mascherare il difetto con ricaricamenti.
Le chiamate esterne sono simulate: il test non invia visite o altri dati reali.
È ignorata solo la notifica Chromium che annulla l'animazione della transizione
quando cambia il viewport; la navigazione e tutte le interazioni devono riuscire.

Queste prove emulano i dispositivi sui due motori browser: non sostituiscono un
collaudo su hardware Android/iPhone né verificano l'aggiornamento del manifest
di una PWA già installata. Dopo il deploy verificare su telefono anche la
rotazione con il blocco rotazione del sistema disattivato.

Riferimenti: [ciclo delle transizioni Astro](https://docs.astro.build/en/guides/view-transitions/)
e [orientamento nel manifest](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/orientation).
