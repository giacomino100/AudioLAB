"""Karaoke Studio: toglie la voce da canzoni e video, cambia tonalità e velocità.

Come è organizzato il pacchetto
-------------------------------
impostazioni.py     tutti i valori regolabili (motori, volume, equalizzatore, cartelle)
elaborazione.py     la sequenza di passaggi eseguita quando si preme "Elabora"
autotest.py         prova automatica completa dell'app (anche dell'.exe)

audio/              le lavorazioni del suono, una per file (non sanno nulla della finestra)
interfaccia/        la finestra e i suoi pannelli (usano audio/ tramite elaborazione.py)

Convenzione usata ovunque: un audio è un array numpy di forma (2, campioni),
stereo, 44 100 campioni al secondo, valori float32 tra -1 e 1.
"""
