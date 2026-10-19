"""Crea il video karaoke: le immagini del video originale con la nuova base."""

import os
import subprocess
import tempfile

from karaoke.audio.file_audio import NASCONDI_CONSOLE, percorso_ffmpeg, salva_audio


def esporta_video(video_originale, audio, percorso_uscita, velocita=1.0):
    """Salva un MP4 con le immagini di video_originale e l'audio dato.

    Se la velocità è cambiata, anche le immagini vengono accelerate o rallentate
    (e quindi ricodificate); altrimenti vengono copiate così come sono.
    """
    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        salva_audio(wav, audio)
        comando_base = [percorso_ffmpeg(), "-y", "-v", "error", "-i", video_originale, "-i", wav,
                        "-map", "0:v:0", "-map", "1:a:0"]
        opzioni_audio = ["-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart"]
        ricodifica = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
        if abs(velocita - 1.0) > 1e-3:
            tentativi = [["-filter:v", f"setpts=PTS/{velocita:.4f}"] + ricodifica]
        else:
            # prima copia le immagini senza ricodificare (veloce e senza perdita di qualità);
            # se il formato non lo permette, le ricodifica
            tentativi = [["-c:v", "copy"], ricodifica]
        errore = ""
        for opzioni_video in tentativi:
            r = subprocess.run(comando_base + opzioni_video + opzioni_audio + [percorso_uscita],
                               capture_output=True, creationflags=NASCONDI_CONSOLE)
            if r.returncode == 0:
                return percorso_uscita
            errore = r.stderr.decode(errors="replace")
        raise RuntimeError("Esportazione del video non riuscita.\n" + errore[-400:])
    finally:
        os.remove(wav)
