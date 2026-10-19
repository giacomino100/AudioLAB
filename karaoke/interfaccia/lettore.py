"""Riproduce l'anteprima: una traccia alla volta (Originale, Base o Voce)."""

import numpy as np
import sounddevice as sd

from karaoke.impostazioni import SR


class Lettore:
    """Cambiando traccia mantiene il punto di ascolto, per confrontare al volo."""

    def __init__(self):
        self.tracce = {}         # nome → audio (campioni, 2): il formato che vuole la scheda audio
        self.attiva = None       # nome della traccia che si sta ascoltando
        self.pos = 0             # posizione attuale, in campioni
        self._flusso = None

    @property
    def audio(self):
        return self.tracce.get(self.attiva)

    def carica(self, tracce, attiva):
        self.ferma()
        self.tracce = {}
        for nome, audio in tracce.items():
            self.sostituisci(nome, audio)
        self.attiva = attiva
        self.pos = 0

    def sostituisci(self, nome, audio):
        """Cambia una traccia anche durante l'ascolto (usato dall'equalizzatore)."""
        self.tracce[nome] = np.ascontiguousarray(audio.T, dtype=np.float32)

    def scegli(self, nome):
        frazione = self.frazione()
        self.attiva = nome
        self.pos = int(frazione * len(self.audio))

    def frazione(self):
        """Dove siamo, da 0 (inizio) a 1 (fine)."""
        a = self.audio
        return self.pos / len(a) if a is not None and len(a) else 0.0

    def secondi(self):
        return self.pos / SR

    def durata(self):
        a = self.audio
        return len(a) / SR if a is not None else 0.0

    def vai(self, frazione):
        a = self.audio
        if a is not None:
            self.pos = int(min(max(frazione, 0), 1) * (len(a) - 1))

    def in_riproduzione(self):
        return self._flusso is not None and self._flusso.active

    def suona(self):
        if self.audio is None:
            return
        self.ferma()
        self._flusso = sd.OutputStream(samplerate=SR, channels=2, dtype="float32",
                                       callback=self._riempi)
        self._flusso.start()

    def ferma(self):
        if self._flusso is not None:
            try:
                self._flusso.stop()
                self._flusso.close()
            except Exception:
                pass
            self._flusso = None

    def _riempi(self, uscita, n_campioni, _tempo, _stato):
        """Chiamata dalla scheda audio ogni pochi millisecondi: le passiamo il pezzo successivo."""
        a = self.audio
        if a is None:
            uscita.fill(0)
            raise sd.CallbackStop
        pezzo = a[self.pos:self.pos + n_campioni]
        uscita[:len(pezzo)] = pezzo
        uscita[len(pezzo):] = 0
        self.pos += len(pezzo)
        if len(pezzo) < n_campioni:          # fine della traccia: si ricomincia dall'inizio
            self.pos = 0
            raise sd.CallbackStop
