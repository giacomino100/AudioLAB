# AudioLAB · Karaoke Studio

App per Windows che **toglie la voce** da canzoni e video, **cambia tonalità e velocità**
e salva la base, la voce o un **video karaoke**.

- Separazione con IA: **Demucs** (Meta) o **MDX-Net** (UVR), in locale sul proprio PC
- **Volume uniforme**: compensa i cali di volume che restano dove c'era la voce
- **Equalizzatore** bassi / medi / alti, automatico e regolabile mentre si ascolta
- Anteprima con forma d'onda: confronto tra Originale, Base e Voce
- Ingresso audio (MP3, WAV, FLAC, M4A…) e video (MP4, MOV, AVI, MKV, WebM)
- Uscita MP3 320 kbps, WAV, FLAC, oppure MP4 con la base al posto dell'audio

Impostazioni predefinite approvate all'ascolto: **Demucs + Volume uniforme "Forte" +
equalizzatore automatico**.

## Avvio dal codice

Serve Python 3.12. Doppio clic su `Avvia Karaoke Studio.bat`: la prima volta crea l'ambiente
in `%LOCALAPPDATA%\KaraokeStudio\venv` e installa le librerie (circa 1 GB per PyTorch).

## Struttura

Il codice è nel pacchetto `karaoke/`: `impostazioni.py` raccoglie i valori regolabili,
`elaborazione.py` contiene la sequenza dei passaggi, `audio/` le lavorazioni del suono,
`interfaccia/` la finestra. Dettagli, test e come creare l'`.exe`: **[STRUTTURA.md](STRUTTURA.md)**.

## Test di qualità

`test/test_qualita.py` controlla che il suono non cambi rispetto alla versione approvata.
I file audio di riferimento (`test/dati/`) non sono nella repo perché derivano da una canzone
protetta da copyright: vanno creati in locale.
