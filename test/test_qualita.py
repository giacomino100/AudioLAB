"""Test di qualità: controlla che il suono non sia cambiato rispetto al riferimento approvato.

Il riferimento (cartella test/dati) è l'uscita della versione approvata all'ascolto il
19/10/2026, con le impostazioni predefinite: Demucs + Volume uniforme "Forte" +
equalizzatore automatico. C'è anche un caso di "controllo" che usa MDX-Net, il volume
"Leggero", la tonalità e la velocità, per verificare anche quelle parti.

Uso (dalla cartella sorgente):
    python test\\test_qualita.py              confronta con il riferimento
    python test\\test_qualita.py --aggiorna   sostituisce il riferimento (solo se il nuovo
                                             suono è stato ascoltato e approvato!)
"""

import json
import os
import random
import sys
import time

import numpy as np

CARTELLA_TEST = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(CARTELLA_TEST))       # per trovare il pacchetto karaoke

from karaoke.elaborazione import Elaboratore, Opzioni  # noqa: E402

DATI = os.path.join(CARTELLA_TEST, "dati")
ESTRATTO = os.path.join(DATI, "estratto.flac")

CASI = {
    "predefinito": dict(),                                     # le impostazioni approvate
    "controllo": dict(motore="MDX-Net", volume_uniforme=0.6, semitoni=-2, velocita=0.9),
}

# Differenza massima accettata, campione per campione (1e-5 ≈ -100 dB: inudibile)
TOLLERANZA = 1e-5


def esegui_caso(elaboratore, opzioni_caso):
    # Demucs sposta la canzone di una frazione di secondo casuale: con il "seme" fisso
    # lo spostamento è sempre lo stesso e il risultato è ripetibile al bit.
    random.seed(0)
    risultato = elaboratore.elabora(Opzioni(file=ESTRATTO, **opzioni_caso))
    return {"Base": risultato.base, "Voce": risultato.voce}


def confronta(nome, nuove, riferimento):
    esito = True
    for traccia in ("Base", "Voce"):
        nuova, attesa = nuove[traccia], riferimento[traccia]
        if nuova.shape != attesa.shape:
            print(f"  ✗ {traccia}: lunghezza diversa {nuova.shape} invece di {attesa.shape}")
            esito = False
            continue
        differenza = float(np.max(np.abs(nuova - attesa)))
        if differenza <= TOLLERANZA:
            print(f"  ✓ {traccia}: identica al riferimento (differenza massima {differenza:.1e})")
        else:
            # quanto è grande la differenza rispetto al suono, in dB (più negativo = più piccola)
            rapporto = 20 * np.log10(np.sqrt(np.mean((nuova - attesa) ** 2))
                                     / np.sqrt(np.mean(attesa ** 2)) + 1e-12)
            print(f"  ✗ {traccia}: DIVERSA dal riferimento (differenza massima {differenza:.1e},"
                  f" {rapporto:.0f} dB rispetto al suono) → va ascoltata prima di accettarla")
            esito = False
    return esito


def main():
    aggiorna = "--aggiorna" in sys.argv
    elaboratore = Elaboratore()
    tutto_ok = True
    for nome, opzioni_caso in CASI.items():
        print(f"Caso «{nome}»: {opzioni_caso or 'impostazioni predefinite'}")
        inizio = time.time()
        nuove = esegui_caso(elaboratore, opzioni_caso)
        print(f"  elaborato in {time.time() - inizio:.0f} s")
        percorso = os.path.join(DATI, f"riferimento_{nome}.npz")
        if aggiorna:
            np.savez_compressed(percorso, **nuove)
            print("  riferimento aggiornato")
            continue
        with np.load(percorso) as riferimento:
            tutto_ok &= confronta(nome, nuove, riferimento)

    if aggiorna:
        info_percorso = os.path.join(DATI, "riferimento.json")
        with open(info_percorso, encoding="utf-8") as f:
            info = json.load(f)
        info["aggiornato"] = time.strftime("%Y-%m-%d %H:%M")
        with open(info_percorso, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        return 0
    print("\nRISULTATO:", "SUONO INVARIATO ✓" if tutto_ok else "IL SUONO È CAMBIATO ✗")
    return 0 if tutto_ok else 1


if __name__ == "__main__":
    sys.exit(main())
