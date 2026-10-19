"""Separazione voce / base con il modello MDX-Net (UVR-MDX-NET Inst HQ3).

Il modello gira con ONNX Runtime, senza PyTorch: funziona anche con Smart App Control attivo.

Come lavora, in breve:
1. la canzone viene divisa in blocchi di circa 6 secondi;
2. ogni blocco viene trasformato in uno "spettrogramma" (le frequenze nel tempo);
3. il modello restituisce lo spettrogramma della sola base;
4. si torna da spettrogramma a suono e si rimettono insieme i blocchi;
5. la voce è quello che resta: originale meno base.
"""

import os
import urllib.request

import numpy as np
import onnxruntime as ort
from numpy.lib.stride_tricks import sliding_window_view

from karaoke.impostazioni import CARTELLA_MODELLI

NOME_MODELLO = "UVR-MDX-NET-Inst_HQ_3.onnx"
URL_MODELLO = ("https://github.com/TRvlvr/model_repo/releases/download/"
               "all_public_uvr_models/" + NOME_MODELLO)

# Parametri fissati dal modello Inst HQ3: non vanno cambiati
N_FFT = 6144            # campioni per ogni "fotografia" delle frequenze
HOP = 1024              # distanza tra due fotografie
DIM_F = 3072            # frequenze che il modello guarda
DIM_T = 256             # fotografie per blocco
COMPENSAZIONE = 1.022   # il modello restituisce la base leggermente più bassa

BLOCCO = HOP * (DIM_T - 1)          # campioni per blocco (~5,9 s)
BORDO = N_FFT // 2                  # bordo scartato a ogni estremità del blocco
UTILE = BLOCCO - 2 * BORDO          # campioni effettivamente usati per blocco
N_FREQUENZE = N_FFT // 2 + 1
# Finestra di Hann "periodica" (come torch.hann_window)
FINESTRA = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N_FFT) / N_FFT)).astype(np.float32)


def percorso_modello():
    return os.path.join(CARTELLA_MODELLI, NOME_MODELLO)


def scarica_modello(avanzamento=None):
    """Scarica il modello la prima volta (circa 65 MB). avanzamento(frazione 0..1)."""
    percorso = percorso_modello()
    if os.path.exists(percorso) and os.path.getsize(percorso) > 60_000_000:
        return percorso
    os.makedirs(CARTELLA_MODELLI, exist_ok=True)
    temporaneo = percorso + ".part"

    def aggiorna(blocchi, dimensione_blocco, totale):
        if avanzamento and totale > 0:
            avanzamento(min(1.0, blocchi * dimensione_blocco / totale))

    urllib.request.urlretrieve(URL_MODELLO, temporaneo, aggiorna)
    os.replace(temporaneo, percorso)
    return percorso


def _spettrogramma(x):
    """Suono (2, BLOCCO) → spettrogramma (1, 4, DIM_F, DIM_T), come lo STFT di torch."""
    pad = N_FFT // 2
    xp = np.pad(x, ((0, 0), (pad, pad)), mode="reflect")
    frames = sliding_window_view(xp, N_FFT, axis=-1)[:, ::HOP]
    spec = np.fft.rfft(frames * FINESTRA, axis=-1)[:, :, :DIM_F].transpose(0, 2, 1)
    # i 4 canali sono: sinistro reale, sinistro immaginario, destro reale, destro immaginario
    out = np.stack([spec.real, spec.imag], axis=1)
    return out.reshape(1, 4, DIM_F, -1).astype(np.float32)


def _da_spettrogramma(y):
    """Spettrogramma (4, DIM_F, DIM_T) → suono (2, BLOCCO). È l'inverso di _spettrogramma."""
    y = y.reshape(2, 2, DIM_F, -1)
    spec = y[:, 0] + 1j * y[:, 1]
    spec = np.pad(spec, ((0, 0), (0, N_FREQUENZE - DIM_F), (0, 0)))
    frames = np.fft.irfft(spec.transpose(0, 2, 1), n=N_FFT, axis=-1) * FINESTRA
    n_frames = frames.shape[1]
    lunghezza = N_FFT + HOP * (n_frames - 1)
    out = np.zeros((2, lunghezza), dtype=np.float64)
    norma = np.zeros(lunghezza, dtype=np.float64)
    finestra_quadra = FINESTRA.astype(np.float64) ** 2
    for t in range(n_frames):                        # sovrappone e somma le fotografie
        s = t * HOP
        out[:, s:s + N_FFT] += frames[:, t]
        norma[s:s + N_FFT] += finestra_quadra
    out /= np.where(norma > 1e-8, norma, 1.0)
    pad = N_FFT // 2
    return out[:, pad:pad + HOP * (n_frames - 1)].astype(np.float32)


class SeparatoreMDX:
    def __init__(self):
        opzioni = ort.SessionOptions()
        opzioni.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sessione = ort.InferenceSession(percorso_modello(), opzioni,
                                             providers=["CPUExecutionProvider"])
        self.nome_ingresso = self.sessione.get_inputs()[0].name

    def _esegui_modello(self, spettrogramma):
        return self.sessione.run(None, {self.nome_ingresso: spettrogramma})[0]

    def separa(self, mix, qualita_extra=False, avanzamento=None, interrompi=None):
        """mix (2, N) → (base, voce), entrambe (2, N).

        qualita_extra: passa ogni blocco due volte (normale e invertito) e fa la media.
        avanzamento(frazione 0..1) e interrompi() → True per annullare: facoltativi.
        """
        n = mix.shape[1]
        pad = UTILE - (n % UTILE)
        mix_p = np.concatenate(
            [np.zeros((2, BORDO), np.float32), mix, np.zeros((2, pad + BORDO), np.float32)],
            axis=1)
        inizi = range(0, n + pad, UTILE)
        totale = len(inizi)
        pezzi = []
        for k, i in enumerate(inizi):
            if interrompi and interrompi():
                raise InterruptedError
            spec = _spettrogramma(mix_p[:, i:i + BLOCCO])
            if qualita_extra:
                previsione = (self._esegui_modello(spec) - self._esegui_modello(-spec)) * 0.5
            else:
                previsione = self._esegui_modello(spec)
            pezzi.append(_da_spettrogramma(previsione[0])[:, BORDO:-BORDO])
            if avanzamento:
                avanzamento((k + 1) / totale)
        base = np.concatenate(pezzi, axis=1)[:, :n]
        voce = mix - base
        return base * COMPENSAZIONE, voce
