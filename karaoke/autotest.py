"""Prova automatica completa dell'app, utile soprattutto per controllare l'.exe.

Uso:  Karaoke Studio.exe --autotest <cartella>
      python karaoke_studio.py --autotest <cartella>

Crea un piccolo video di prova, lo elabora con tutti i motori disponibili, prova
l'equalizzatore e i tre salvataggi (base, voce, video). Scrive tutto in <cartella>/autotest.log.
"""

import os
import subprocess
import traceback

import numpy as np

from karaoke.audio.file_audio import NASCONDI_CONSOLE, percorso_ffmpeg


def _crea_video_di_prova(percorso):
    subprocess.run([percorso_ffmpeg(), "-y", "-v", "error",
                    "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                    "-t", "8", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", percorso], check=True, creationflags=NASCONDI_CONSOLE)


def _attendi_fine(finestra):
    """Aspetta che il lavoro in background finisca e passa i messaggi alla finestra."""
    finestra.lavoro.join()
    ultimo = None
    while not finestra.messaggi.empty():
        ultimo = finestra.messaggi.get()
        finestra.gestisci_messaggio(ultimo)
    return ultimo


def esegui(cartella):
    from karaoke.interfaccia.finestra import Finestra

    with open(os.path.join(cartella, "autotest.log"), "w", encoding="utf-8") as log:
        def scrivi(*parti):
            print(*parti, file=log, flush=True)

        try:
            video = os.path.join(cartella, "prova.mp4")
            _crea_video_di_prova(video)
            finestra = Finestra()
            impostazioni, risultato = finestra.impostazioni, finestra.risultato
            scrivi("trascinamento:", finestra.trascinamento)
            scrivi("motori:", impostazioni.motore.cget("values"))
            scrivi("predefiniti:", impostazioni.motore.get(), "+", impostazioni.volume.get())
            finestra.apri_file(video)

            for motore in impostazioni.motore.cget("values"):
                impostazioni.motore.set(motore)
                impostazioni.semitoni.set(2)
                finestra.elabora_o_annulla()
                esito = _attendi_fine(finestra)
                scrivi(motore, esito[0], sorted(risultato.tracce))
            finestra.update()

            scrivi("eq automatica:", risultato.risultato.eq)
            prima = risultato.tracce["Base"].copy()
            risultato.eq_cursori["bassi"].set(-6)
            risultato.eq_ricalcola()
            risultato._eq_pronto(risultato._eq_coda.get(timeout=60))
            scrivi("eq manuale: base cambiata:", not np.allclose(prima, risultato.tracce["Base"]),
                   "lettore aggiornato:",
                   risultato.lettore.tracce["Base"].shape[0] == risultato.tracce["Base"].shape[1])

            for tipo, nome in (("Base", "base.mp3"), ("Voce", "voce.wav"), ("Video", "karaoke.mp4")):
                percorso = os.path.join(cartella, nome)
                finestra._in_background(finestra._salva, (tipo, percorso), "")
                esito = _attendi_fine(finestra)
                scrivi("salva", tipo, esito[0], os.path.exists(percorso) and os.path.getsize(percorso))
            finestra.destroy()
        except Exception:
            traceback.print_exc(file=log)
