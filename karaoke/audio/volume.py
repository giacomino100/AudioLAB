"""Volume uniforme: riempie i cali di volume della base.

Il problema: nelle canzoni masterizzate un compressore abbassa la musica ogni volta che
entra la voce, per farla emergere. Tolta la voce, quei cali restano e la base "fa alti e
bassi". Questo file li compensa.
"""

import numpy as np
from pedalboard import Limiter

from karaoke.impostazioni import SR


def _media_mobile(x, n):
    """Smussa la curva x facendo la media su n valori consecutivi."""
    n = max(1, int(n))
    k = np.ones(n) / n
    return np.convolve(np.pad(x, (n, n), mode="edge"), k, "same")[n:-n]


def livella(base, mix, forza=0.6):
    """Restituisce la base con il volume più regolare.

    base, mix: (2, N) — la base separata e la canzone originale.
    forza: 0 = nessun effetto, 0.6 = "Leggero", 1.0 = "Forte".

    Due correzioni, misurate su blocchi di 20 millisecondi:
    1. anti-pompaggio: rialza i cali brevi (decimi di secondo) rispetto all'andamento della base;
    2. parti basse: avvicina le parti molto più basse al livello medio del brano.
    Le pause vere (dove anche l'originale è silenzioso) non vengono toccate.
    Alla fine un limitatore evita che i picchi distorcano.
    """
    if forza <= 0:
        return base
    durata_blocco = 0.02                              # secondi
    campioni_blocco = int(SR * durata_blocco)

    def volume_db(x):
        """Volume di ogni blocco, in decibel."""
        energia = (x.astype(np.float64) ** 2).mean(0)
        k = len(energia) // campioni_blocco
        return 10 * np.log10(energia[:k * campioni_blocco].reshape(k, campioni_blocco).mean(1)
                             + 1e-10)

    vol_base, vol_mix = volume_db(base), volume_db(mix)
    if len(vol_base) < 10:
        return base

    # 1. anti-pompaggio: andamento lento (4 s) meno andamento breve (0,15 s)
    lento = _media_mobile(vol_base, 4 / durata_blocco)
    rialzo_db = np.clip(lento - _media_mobile(vol_base, 0.15 / durata_blocco), 0, 12) * forza

    # 2. parti basse: confronto con il livello mediano delle parti "attive" del brano
    sezioni = _media_mobile(vol_base, 3 / durata_blocco)
    attivo = vol_mix > np.percentile(vol_mix, 20)
    mediana = np.median(sezioni[attivo]) if attivo.any() else np.median(sezioni)
    rialzo_db += np.clip(mediana - 3 - sezioni, 0, 9) * forza

    # pause vere: l'originale è molto sotto il suo andamento → nessun rialzo
    rialzo_db *= vol_mix > _media_mobile(vol_mix, 4 / durata_blocco) - 12
    rialzo_db *= vol_mix > np.max(vol_mix) - 50

    # da un valore per blocco a un valore per campione, con passaggi morbidi
    rialzo_db = _media_mobile(rialzo_db, 0.12 / durata_blocco)
    centri = (np.arange(len(rialzo_db)) + 0.5) * campioni_blocco
    guadagno = (10 ** (np.interp(np.arange(base.shape[1]), centri, rialzo_db) / 20)
                ).astype(np.float32)
    out = base * guadagno
    limitatore = Limiter(threshold_db=-1.0, release_ms=120)
    return limitatore(out, SR).astype(np.float32)
