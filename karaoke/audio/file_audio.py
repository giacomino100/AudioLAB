"""Leggere e salvare file audio, leggere l'audio dai video."""

import os
import subprocess

import numpy as np
from pedalboard.io import AudioFile

from karaoke.impostazioni import ESTENSIONI_VIDEO, SR

# Ritardo (in campioni) che il codificatore MP3 aggiunge all'inizio del file:
# lo togliamo in salvataggio, così la base resta a tempo con l'originale e con il video.
RITARDO_MP3 = 1105

# Su Windows impedisce a ffmpeg di aprire una finestra nera di console
NASCONDI_CONSOLE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def percorso_ffmpeg():
    """Percorso del programma ffmpeg incluso nella libreria imageio-ffmpeg."""
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def e_un_video(percorso):
    return os.path.splitext(percorso)[1].lower() in ESTENSIONI_VIDEO


def carica_audio(percorso):
    """Legge un file audio o video e restituisce un array (2, campioni) a 44,1 kHz stereo."""
    if not e_un_video(percorso):
        try:
            with AudioFile(percorso).resampled_to(SR) as f:
                audio = f.read(f.frames)
            if audio.shape[0] == 1:                 # mono → stereo
                audio = np.repeat(audio, 2, axis=0)
            return audio[:2].astype(np.float32)
        except Exception:
            pass  # formato che pedalboard non legge (m4a, aac, wma…): ci pensa ffmpeg
    return _carica_con_ffmpeg(percorso)


def _carica_con_ffmpeg(percorso):
    comando = [percorso_ffmpeg(), "-v", "error", "-i", percorso, "-vn", "-ac", "2",
               "-ar", str(SR), "-f", "f32le", "-"]
    r = subprocess.run(comando, capture_output=True, creationflags=NASCONDI_CONSOLE)
    if r.returncode != 0 or not r.stdout:
        righe = r.stderr.decode(errors="replace").strip().splitlines()
        raise RuntimeError("Nessuna traccia audio leggibile nel file.\n" + "\n".join(righe[-3:]))
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).T.copy()


def durata_file(percorso):
    """Durata in secondi (anche per i video), senza leggere tutto il file."""
    if not e_un_video(percorso):
        try:
            with AudioFile(percorso) as f:
                return f.duration
        except Exception:
            pass
    r = subprocess.run([percorso_ffmpeg(), "-hide_banner", "-i", percorso],
                       capture_output=True, creationflags=NASCONDI_CONSOLE)
    testo = r.stderr.decode(errors="replace")
    i = testo.find("Duration: ")                     # ffmpeg scrive "Duration: 00:03:28.15"
    if i < 0:
        raise RuntimeError("Il file non sembra un audio o un video valido.")
    ore, minuti, secondi = testo[i + 10:i + 21].split(":")
    return int(ore) * 3600 + int(minuti) * 60 + float(secondi)


def salva_audio(percorso, audio, sr=SR):
    """Salva in MP3 (320 kbps), WAV o FLAC, in base all'estensione del percorso."""
    estensione = os.path.splitext(percorso)[1].lower()
    opzioni = {"quality": "320k"} if estensione == ".mp3" else {}
    picco = float(np.max(np.abs(audio))) if audio.size else 0.0
    if picco > 1.0:                                  # evita la distorsione
        audio = audio / picco
    if estensione == ".mp3":
        # anticipa l'audio del ritardo del codificatore, così resta a tempo con l'originale
        audio = np.concatenate(
            [audio[:, RITARDO_MP3:], np.zeros((audio.shape[0], RITARDO_MP3), audio.dtype)], axis=1)
    with AudioFile(percorso, "w", sr, audio.shape[0], **opzioni) as f:
        f.write(audio)
