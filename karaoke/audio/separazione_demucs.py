"""Separazione voce / base con Demucs di Meta (richiede PyTorch).

Demucs divide la canzone in 4 parti: voce, batteria, basso e "altro".
La base è la somma di batteria + basso + altro.
"""

import os

import numpy as np

from karaoke.impostazioni import SR


class _Annullato(BaseException):
    """Serve a interrompere Demucs dall'interno della sua funzione di avanzamento."""


def demucs_disponibile():
    """False se PyTorch non si carica (per esempio con Smart App Control attivo)."""
    try:
        import torch  # noqa: F401
        import demucs.api  # noqa: F401
        return True
    except BaseException:
        return False


class SeparatoreDemucs:
    def __init__(self, nome_modello="htdemucs"):
        """nome_modello: "htdemucs" (Demucs) oppure "htdemucs_ft" (Demucs Pro, 4 volte più lento)."""
        import torch
        torch.set_num_threads(os.cpu_count() or 4)
        self.nome_modello = nome_modello

    def separa(self, mix, qualita_extra=False, avanzamento=None, interrompi=None):
        """mix (2, N) → (base, voce), entrambe (2, N).

        qualita_extra: il modello lavora due volte con lo spostamento casuale ("shifts")
        e fa la media. Anche con qualità normale Demucs sposta la canzone di una frazione
        di secondo casuale: per questo due elaborazioni non sono identiche al bit.
        """
        import torch
        from demucs.api import Separator

        passate = 2 if qualita_extra else 1

        def aggiorna(info):
            if interrompi and interrompi():
                raise _Annullato
            if avanzamento and info.get("state") == "end":
                totale = info["models"] * passate
                fatto = info["model_idx_in_bag"] * passate + info["shift_idx"]
                fatto += min(1.0, info["segment_offset"] / max(1, info["audio_length"]))
                avanzamento(min(1.0, fatto / totale))

        separatore = Separator(model=self.nome_modello, device="cpu", shifts=passate,
                               callback=aggiorna)
        try:
            with torch.inference_mode():
                _, parti = separatore.separate_tensor(torch.from_numpy(mix), SR)
        except _Annullato:
            raise InterruptedError
        voce = parti["vocals"].numpy()
        base = sum(v.numpy() for k, v in parti.items() if k != "vocals")
        if avanzamento:
            avanzamento(1.0)
        return base.astype(np.float32), voce.astype(np.float32)
