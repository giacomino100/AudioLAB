"""Equalizzatore a tre bande: bassi, medi, alti.

Togliendo la voce si toglie soprattutto energia dai medi, dove vive la voce:
la base risulta "rimbombante e vuota". L'equalizzatore riequilibra il timbro.
"""

import numpy as np
from pedalboard import Limiter

from karaoke.impostazioni import BANDE, SR


def _energia_bande(audio):
    """Energia media (in dB) di bassi, medi e alti, misurata su tutto il brano."""
    m = audio.mean(0).astype(np.float64)                 # stereo → mono
    n = 8192                                             # blocchi da ~0,19 s
    k = len(m) // n
    if k < 1:
        return {b: 0.0 for b in BANDE}
    passo = max(1, k // 400)                             # bastano ~400 blocchi
    blocchi = m[:k * n].reshape(k, n)[::passo] * np.hanning(n)
    spettro = (np.abs(np.fft.rfft(blocchi, axis=1)) ** 2).mean(0)
    f = np.fft.rfftfreq(n, 1 / SR)
    return {b: 10 * np.log10(spettro[(f >= lo) & (f < hi)].sum() + 1e-12)
            for b, (lo, hi) in BANDE.items()}


def eq_automatica(base, mix):
    """Propone i valori di bassi/medi/alti (in dB) per avvicinare la base all'originale.

    I bassi quasi non cambiano togliendo la voce, quindi fanno da riferimento: si misura
    quanto medi e alti sono calati rispetto ai bassi e se ne recupera la metà (di più
    farebbe riemergere i residui di voce). Poi i tre valori vengono centrati sullo zero:
    un po' meno bassi, un po' più medi e alti.
    """
    energia_base, energia_mix = _energia_bande(base), _energia_bande(mix)
    calo = {b: (energia_mix[b] - energia_base[b]) - (energia_mix["bassi"] - energia_base["bassi"])
            for b in BANDE}
    valori = {"bassi": 0.0,
              "medi": float(np.clip(calo["medi"] * 0.5, 0, 6)),
              "alti": float(np.clip(calo["alti"] * 0.5, 0, 4))}
    media = sum(valori.values()) / 3
    return {b: round(v - media, 1) for b, v in valori.items()}


def equalizza(audio, bassi=0.0, medi=0.0, alti=0.0):
    """Applica i tre filtri (valori in dB) mantenendo lo stesso volume complessivo."""
    if not (bassi or medi or alti):
        return audio
    from pedalboard import HighShelfFilter, LowShelfFilter, PeakFilter, Pedalboard

    filtri = Pedalboard([
        LowShelfFilter(cutoff_frequency_hz=200, gain_db=float(bassi), q=0.7),
        PeakFilter(cutoff_frequency_hz=1200, gain_db=float(medi), q=0.5),
        HighShelfFilter(cutoff_frequency_hz=5000, gain_db=float(alti), q=0.7),
    ])
    out = filtri(audio, SR)
    # riporta il volume a quello di prima, così si confronta solo il timbro
    prima = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)) + 1e-12)
    dopo = float(np.sqrt(np.mean(out.astype(np.float64) ** 2)) + 1e-12)
    out = out * np.float32(prima / dopo)
    return Limiter(threshold_db=-1.0, release_ms=120)(out, SR).astype(np.float32)
