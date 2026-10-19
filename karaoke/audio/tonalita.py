"""Cambio di tonalità e velocità con Rubber Band (tramite la libreria pedalboard)."""

import numpy as np
from pedalboard import time_stretch

from karaoke.impostazioni import SR


def cambia_tono(audio, semitoni=0, velocita=1.0):
    """semitoni: da -12 a +12 (0 = tonalità originale).
    velocita: 1.0 = originale, 0.9 = 90% (più lento), 1.1 = 110% (più veloce).
    La tonalità non cambia la velocità, e viceversa.
    """
    if semitoni == 0 and abs(velocita - 1.0) < 1e-3:
        return audio
    out = time_stretch(
        audio,
        SR,
        stretch_factor=float(velocita),
        pitch_shift_in_semitones=float(semitoni),
        high_quality=True,
        transient_mode="crisp",
    )
    return out.astype(np.float32)
