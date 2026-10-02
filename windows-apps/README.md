# App Windows Dediche Musicali

Quattro app web in finestre Microsoft Edge o Google Chrome senza barra degli indirizzi:
DDGPilli sito, DDGPilli admin, Dediche FF sito e Dediche FF admin.

Eseguire `Installa.cmd`. Non servono privilegi amministrativi.
L'installazione crea collegamenti sul Desktop e nel menu Start e conserva
icone e profili in `%LOCALAPPDATA%\DedicheMusicaliApps`.
Ogni app ha un profilo separato: al primo accesso potrebbe richiedere il login.
Serve una connessione Internet. Gli aggiornamenti dei siti sono automatici.
Sono app web basate sul browser, non eseguibili nativi autonomi.
L'installer cerca Edge nel registro di Windows, nel PATH e nelle cartelle
standard; se non lo trova, cerca Chrome. Serve almeno uno dei due browser.
Per un percorso personalizzato, da PowerShell eseguire:

```powershell
.\install.ps1 -BrowserPath 'C:\percorso\chrome.exe'
```

L'opzione `-CheckOnly` verifica il browser senza creare collegamenti.

Per rimuovere i collegamenti, eliminarli dal Desktop e dalla cartella
`Dediche musicali` del menu Start. La cartella locale contiene anche le sessioni
di accesso: eliminarla solo se si desidera cancellare questi dati.
