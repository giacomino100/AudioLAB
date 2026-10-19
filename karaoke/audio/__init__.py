"""Lavorazioni del suono, una per file.

file_audio.py           leggere e salvare audio e video
separazione_mdx.py      separare voce e base con il modello MDX-Net (ONNX)
separazione_demucs.py   separare voce e base con Demucs (PyTorch)
volume.py               "Volume uniforme": riempie i cali di volume della base
equalizzatore.py        bassi / medi / alti, anche in automatico
tonalita.py             cambio di tonalità e velocità
video.py                crea il video karaoke

Nessuno di questi file conosce la finestra: ricevono e restituiscono array numpy.
"""
