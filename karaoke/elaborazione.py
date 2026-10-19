"""La "ricetta" di Karaoke Studio: cosa succede quando si preme "Elabora".

    file audio/video
       │ 1. lettura
       ▼
    originale ──► 2. separazione IA ──► base + voce
                        │
                        ▼
                  3. volume uniforme (base)
                        ▼
                  4. tonalità e velocità (base e voce)
                        ▼
                  5. equalizzatore automatico (base)
                        ▼
                    Risultato  →  anteprima e salvataggio

Questo file non conosce la finestra: si può usare anche da un test o da uno script.
"""

import os
import time
from dataclasses import dataclass, field

import numpy as np

from karaoke import impostazioni
from karaoke.audio.equalizzatore import eq_automatica, equalizza
from karaoke.audio.file_audio import carica_audio
from karaoke.audio.tonalita import cambia_tono
from karaoke.audio.volume import livella


@dataclass
class Opzioni:
    """Le scelte fatte nella finestra. I valori predefiniti sono quelli approvati all'ascolto."""
    file: str
    togli_voce: bool = True
    motore: str = impostazioni.MOTORE_PREDEFINITO
    qualita_extra: bool = False
    volume_uniforme: float = impostazioni.VOLUME_UNIFORME[impostazioni.VOLUME_PREDEFINITO]
    semitoni: int = 0
    velocita: float = 1.0                             # 1.0 = 100%

    def cambia_tono_o_velocita(self):
        return self.semitoni != 0 or abs(self.velocita - 1) > 1e-3


@dataclass
class Risultato:
    opzioni: Opzioni
    originale: np.ndarray
    base_senza_eq: np.ndarray       # base prima dell'equalizzatore (serve ai cursori)
    base: np.ndarray                # base finale, con l'equalizzatore automatico
    voce: np.ndarray = None         # None se "Togli la voce" è spento
    eq: dict = field(default_factory=lambda: {"bassi": 0.0, "medi": 0.0, "alti": 0.0})

    def tracce(self):
        """Le tracce da ascoltare, nell'ordine dei pulsanti dell'anteprima."""
        tracce = {"Originale": self.originale, "Base": self.base}
        if self.voce is not None:
            tracce["Voce"] = self.voce
        return tracce


class Elaboratore:
    """Esegue la ricetta. Ricorda l'ultima separazione: se cambi solo tonalità, velocità o
    volume e premi di nuovo "Elabora", la separazione (la parte lenta) non viene rifatta."""

    def __init__(self):
        self._memoria = {}           # (file, qualità extra, motore) → (base, voce)

    def elabora(self, opzioni, avanzamento=None, interrompi=None):
        """avanzamento(testo, frazione 0..1) e interrompi() → True: facoltativi."""
        avanzamento = avanzamento or (lambda testo, frazione: None)
        interrompi = interrompi or (lambda: False)

        # 1. lettura
        avanzamento("Leggo il file…", 0.02)
        originale = carica_audio(opzioni.file)

        # 2. separazione e 3. volume uniforme
        if opzioni.togli_voce:
            base, voce = self._separa(originale, opzioni, avanzamento, interrompi)
            if opzioni.volume_uniforme > 0:
                avanzamento("Rendo uniforme il volume della base…", 0.77)
                base = livella(base, originale, opzioni.volume_uniforme)
        else:
            base, voce = originale, None

        # 4. tonalità e velocità
        base_finale, voce_finale = base, voce
        da_fare = [("Base", base)] + ([("Voce", voce)] if voce is not None else [])
        for i, (nome, audio) in enumerate(da_fare):
            if interrompi():
                raise InterruptedError
            if opzioni.cambia_tono_o_velocita():
                avanzamento(f"Cambio tonalità e velocità ({nome.lower()})…",
                            0.8 + 0.18 * i / len(da_fare))
                audio = cambia_tono(audio, opzioni.semitoni, opzioni.velocita)
            if nome == "Base":
                base_finale = audio
            else:
                voce_finale = audio

        # 5. equalizzatore automatico (misurato prima del cambio di tonalità)
        eq = {"bassi": 0.0, "medi": 0.0, "alti": 0.0}
        if opzioni.togli_voce:
            avanzamento("Riequilibro bassi, medi e alti…", 0.98)
            eq = eq_automatica(base, originale)

        return Risultato(opzioni=opzioni, originale=originale, base_senza_eq=base_finale,
                         base=equalizza(base_finale, **eq), voce=voce_finale, eq=eq)

    def _separa(self, originale, opzioni, avanzamento, interrompi):
        chiave = (opzioni.file, opzioni.qualita_extra, opzioni.motore)
        if chiave not in self._memoria:
            separatore = self._prepara_separatore(opzioni.motore, avanzamento)
            inizio = time.time()

            def aggiorna(frazione):
                trascorso = time.time() - inizio
                resto = trascorso / frazione - trascorso if frazione > 0.02 else 0
                mancano = f" · mancano ~{formatta_durata(resto)}" if resto else ""
                avanzamento(f"Separo la voce… {int(frazione * 100)}%{mancano}",
                            0.1 + 0.65 * frazione)

            # si tiene solo l'ultima separazione, per non occupare troppa memoria
            self._memoria = {chiave: separatore.separa(originale, opzioni.qualita_extra,
                                                       aggiorna, interrompi)}
        return self._memoria[chiave]

    @staticmethod
    def _prepara_separatore(motore, avanzamento):
        if motore == "MDX-Net":
            from karaoke.audio.separazione_mdx import (SeparatoreMDX, percorso_modello,
                                                       scarica_modello)
            if not os.path.exists(percorso_modello()):
                scarica_modello(lambda p: avanzamento(
                    f"Scarico il modello IA (solo la prima volta)… {int(p * 100)}%", 0.1 * p))
            avanzamento("Avvio il modello IA…", 0.1)
            return SeparatoreMDX()
        from karaoke.audio.separazione_demucs import SeparatoreDemucs
        avanzamento("Avvio Demucs (la prima volta scarica il modello)…", 0.1)
        return SeparatoreDemucs(impostazioni.MODELLI_DEMUCS[motore])


def formatta_durata(secondi):
    """125 → "2:05"."""
    secondi = int(round(max(0, secondi)))
    return f"{secondi // 60}:{secondi % 60:02d}"
