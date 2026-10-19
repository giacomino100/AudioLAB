# Karaoke Studio – Struttura del codice e delle cartelle

Programma per Windows che toglie la voce da canzoni e video, cambia tonalità e velocità,
riequilibra il suono e salva la base, la voce o un video karaoke.
Scritto in Python, distribuito come `.exe` creato con PyInstaller.

> **Qualità di riferimento** – Le impostazioni predefinite (**Demucs + Volume uniforme
> "Forte" + equalizzatore automatico**) sono state approvate all'ascolto il 19/10/2026.
> Il suono che producono è salvato in `test/dati/`. Prima di distribuire qualsiasi modifica,
> lancia il test di qualità (vedi §6): deve rispondere **SUONO INVARIATO ✓**.

---

## 1. Cartelle sul Desktop

```
Desktop\Karaoke Studio\
├── Karaoke Studio\            ← il PROGRAMMA PRONTO: avvia "Karaoke Studio.exe"
├── Karaoke Studio.zip         ← lo stesso programma compresso, da dare ad altri
├── sorgente\                  ← il CODICE (vedi sotto)
└── backup\                    ← copie del codice prima delle modifiche importanti
```

## 2. Il codice: un file per ogni compito

```
sorgente\
├── karaoke_studio.py              avvio: apre la finestra (o l'autotest)
├── karaoke\
│   ├── impostazioni.py            ★ TUTTI i valori regolabili, in un posto solo
│   ├── elaborazione.py            ★ la "ricetta": i passaggi di "Elabora", in ordine
│   ├── autotest.py                prova automatica completa (anche dell'.exe)
│   │
│   ├── audio\                     LAVORAZIONI DEL SUONO (non sanno nulla della finestra)
│   │   ├── file_audio.py          leggere/salvare audio, leggere l'audio dei video
│   │   ├── separazione_mdx.py     togliere la voce con MDX-Net (ONNX, senza PyTorch)
│   │   ├── separazione_demucs.py  togliere la voce con Demucs (PyTorch)
│   │   ├── volume.py              "Volume uniforme": riempire i cali di volume
│   │   ├── equalizzatore.py       bassi / medi / alti, anche in automatico
│   │   ├── tonalita.py            cambio di tonalità e velocità
│   │   └── video.py               creare il video karaoke
│   │
│   └── interfaccia\               LA FINESTRA
│       ├── finestra.py            collega i due pannelli, lancia i lavori lunghi
│       ├── pannello_impostazioni.py   colonna sinistra (file, voce, tonalità, Elabora)
│       ├── pannello_risultato.py      colonna destra (anteprima, equalizzatore, Scarica)
│       ├── lettore.py             riproduce l'anteprima
│       ├── forma_onda.py          la forma d'onda cliccabile
│       ├── stile.py               colori e pulsanti riutilizzati
│       └── testi.py               testi mostrati all'utente, nomi dei file salvati
│
├── test\
│   ├── test_qualita.py            ★ controlla che il suono non sia cambiato
│   └── dati\                      estratto di prova e suono di riferimento approvato
│
├── requirements.txt               librerie Python necessarie
├── icona.ico                      icona dell'app
├── Avvia Karaoke Studio.bat       avvio dal codice, senza .exe (installa tutto la 1ª volta)
└── STRUTTURA.md                   questo documento
```

**Da dove cominciare a leggere:** `impostazioni.py` → `elaborazione.py` → i file in `audio\`.
L'interfaccia si legge per ultima. Ogni file inizia con una spiegazione di cosa fa.

### La regola principale: audio e finestra sono separati

```
   interfaccia\  ──usa──►  elaborazione.py  ──usa──►  audio\
   (cosa vede l'utente)    (in che ordine)            (come si lavora il suono)
```

- I file in `audio\` ricevono e restituiscono **array numpy** di forma `(2, campioni)`:
  stereo, 44 100 campioni al secondo, valori tra −1 e 1. Non aprono finestre.
- `elaborazione.py` non conosce la finestra: per questo lo usa anche il test di qualità.
- L'interfaccia non fa calcoli sul suono: raccoglie le scelte e mostra i risultati.

## 3. Cosa succede quando si preme "Elabora" (`elaborazione.py`)

```
file audio/video
   │ 1. lettura                             audio/file_audio.py
   ▼
originale ──► 2. separazione IA ──► base + voce        audio/separazione_*.py
                    │   (la separazione resta in memoria: cambiando solo tonalità,
                    │    velocità o volume non viene rifatta)
                    ▼
              3. volume uniforme (base)      audio/volume.py
                    ▼
              4. tonalità e velocità         audio/tonalita.py
                    ▼
              5. equalizzatore automatico    audio/equalizzatore.py
                    ▼
              Risultato ──► anteprima ──► Salva base / voce / video karaoke
```

Le scelte dell'utente viaggiano in un oggetto **`Opzioni`**, il prodotto finale in un
oggetto **`Risultato`** (entrambi definiti in `elaborazione.py`).

### Come la finestra resta reattiva (`interfaccia/finestra.py`)

Elaborazione e salvataggio girano in un **thread** separato. Il thread non tocca la
finestra: manda messaggi in una coda (`"stato"`, `"fatto"`, `"salvato"`, `"annullato"`,
`"errore"`) che la finestra legge ogni 60 millisecondi.

## 4. Cartelle create dal programma sul PC

| Percorso | Contenuto |
|---|---|
| `%LOCALAPPDATA%\KaraokeStudio\models\` | Modello MDX-Net (circa 65 MB), scaricato al primo uso |
| `%USERPROFILE%\.cache\torch\hub\checkpoints\` | Modelli Demucs (circa 80 MB, più circa 320 MB per Demucs Pro), scaricati al primo uso |
| `%LOCALAPPDATA%\KaraokeStudio\venv\` | Ambiente Python, solo se usi `Avvia Karaoke Studio.bat` |

## 5. Librerie usate

| Libreria | A cosa serve |
|---|---|
| `onnxruntime` | Esegue il modello MDX-Net |
| `torch`, `demucs` | Motori Demucs |
| `pedalboard` | Audio in/out, tonalità (Rubber Band), filtri dell'equalizzatore, limitatore |
| `imageio-ffmpeg` | ffmpeg incluso: lettura dei video ed esportazione del video karaoke |
| `customtkinter`, `tkinterdnd2` | Interfaccia grafica e trascinamento dei file |
| `sounddevice` | Ascolto dell'anteprima |
| `numpy` | Calcoli sull'audio |

## 6. Test

Dalla cartella `sorgente`, con l'ambiente Python installato:

```bat
"%LOCALAPPDATA%\KaraokeStudio\venv\Scripts\python.exe" test\test_qualita.py
```

- Elabora 15 secondi di prova con le impostazioni predefinite, più un caso di controllo
  (MDX-Net, volume "Leggero", tonalità −2, velocità 90%). Ci vogliono circa 40 secondi.
- Confronta campione per campione con il suono approvato. Risponde **SUONO INVARIATO ✓**
  oppure dice quale traccia è cambiata e di quanto.
- Se un cambiamento del suono è **voluto** ed è stato **ascoltato e approvato**, il riferimento
  si aggiorna con `test\test_qualita.py --aggiorna`.

L'**autotest** prova invece tutta l'app (finestra, motori, equalizzatore, salvataggi):
`"Karaoke Studio.exe" --autotest C:\una\cartella` scrive `autotest.log` in quella cartella.

> Nota: `test\dati\estratto.flac` sono 15 secondi di un Inno ACR, usati solo per il test:
> non includere la cartella `test\dati` se condividi il codice pubblicamente.

## 7. Come rigenerare il programma `.exe`

Dalla cartella `sorgente`:

```bat
"%LOCALAPPDATA%\KaraokeStudio\venv\Scripts\python.exe" -m pip install pyinstaller
"%LOCALAPPDATA%\KaraokeStudio\venv\Scripts\python.exe" -m PyInstaller --noconfirm --windowed ^
  --name "Karaoke Studio" --icon icona.ico --add-data "icona.ico;." ^
  --collect-all customtkinter --collect-all demucs --collect-all sounddevice ^
  --collect-all _sounddevice_data --collect-all pedalboard --collect-all onnxruntime ^
  --collect-all imageio_ffmpeg --collect-all tkinterdnd2 --collect-submodules julius ^
  --collect-submodules karaoke ^
  --copy-metadata demucs --copy-metadata torch --copy-metadata tqdm ^
  --copy-metadata huggingface_hub --copy-metadata imageio_ffmpeg karaoke_studio.py
```

Il programma esce in `dist\Karaoke Studio\`. Prima di distribuirlo: test di qualità e autotest.

## 8. Cose da sapere

- **Smart App Control** di Windows blocca PyTorch. Se è attivo, l'app mostra solo MDX-Net.
- L'`.exe` **non è firmato**: sugli altri PC Windows può mostrare un avviso ("Esegui comunque").
- Tutto gira **sul processore**: una canzone di 4 minuti richiede circa 4–5 minuti con MDX-Net o Demucs, circa 18 con Demucs Pro.
- Demucs sposta la canzone di una frazione di secondo **casuale** prima di separarla, quindi
  due elaborazioni non sono identiche al bit (all'orecchio non si sente). Il test fissa il caso
  ("seme") per poter confrontare con precisione.
