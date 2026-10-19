"""Tutti i valori regolabili di Karaoke Studio, raccolti in un unico posto.

ATTENZIONE: le impostazioni predefinite (Demucs + Volume uniforme "Forte" + equalizzatore
automatico) sono quelle approvate all'ascolto il 19/10/2026. Prima di cambiare un valore
che tocca il suono, lancia il test di qualità: test/test_qualita.py
"""

import os

# ---------------------------------------------------------------- audio
# Frequenza di campionamento usata in tutto il programma (campioni al secondo)
SR = 44100

ESTENSIONI_VIDEO = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv")

# ---------------------------------------------------------------- cartelle
# Dove l'app salva i modelli scaricati (es. C:\Users\<nome>\AppData\Local\KaraokeStudio)
CARTELLA_APP = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                            "KaraokeStudio")
CARTELLA_MODELLI = os.path.join(CARTELLA_APP, "models")

# ---------------------------------------------------------------- motori IA
# nome mostrato: (descrizione, minuti di calcolo per ogni minuto di canzone)
MOTORI = {
    "MDX-Net": ("Veloce e senza PyTorch · ottimo per karaoke", 1.2),
    "Demucs": ("Meta htdemucs · base più naturale e piena", 1.1),
    "Demucs Pro": ("Meta htdemucs_ft · la massima qualità, ma molto lento", 4.5),
}
# Nome interno del modello Demucs per ciascun motore
MODELLI_DEMUCS = {"Demucs": "htdemucs", "Demucs Pro": "htdemucs_ft"}
MOTORE_PREDEFINITO = "Demucs"

# ---------------------------------------------------------------- volume uniforme
# nome mostrato: forza del livellatore (0 = spento, 1 = massimo)
VOLUME_UNIFORME = {"Spento": 0.0, "Leggero": 0.6, "Forte": 1.0}
DESCRIZIONI_VOLUME = {
    "Spento": "La base resta com'è uscita dal modello",
    "Leggero": "Attenua i cali di volume dove c'era la voce",
    "Forte": "Volume regolare come l'originale · consigliato",
}
VOLUME_PREDEFINITO = "Forte"

# ---------------------------------------------------------------- equalizzatore
# Le tre bande misurate e regolate (in Hz)
BANDE = {"bassi": (20, 250), "medi": (250, 4000), "alti": (4000, 16000)}
# Escursione massima dei cursori (in dB)
EQ_MAX = 12.0

# ---------------------------------------------------------------- tonalità e velocità
SEMITONI_MAX = 12
VELOCITA_MIN, VELOCITA_MAX = 50, 150   # in percentuale
