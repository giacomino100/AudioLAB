"""Colori e piccoli elementi grafici usati in tutta la finestra.

I colori scritti come coppia ("#chiaro", "#scuro") cambiano da soli con il tema.
"""

import os
import sys

import customtkinter as ctk

VIOLA = "#7C5CFF"
VIOLA_HOVER = "#6846F0"
VERDE = "#1F9D74"
VERDE_HOVER = "#18805E"
ROSSO = "#D9455F"
ROSSO_HOVER = "#C23450"
SFONDO = ("#F2F3F7", "#14151A")
SFONDO_CARD = ("#FFFFFF", "#1E1F26")
BORDO = ("#C9CBD6", "#3A3D4A")
TESTO = ("#222222", "#EEEEEE")
TESTO_TENUE = ("#6B6F7B", "#9A9DAA")
NEUTRO = ("#E4E5EC", "#2A2C35")
NEUTRO_HOVER = ("#D5D7E0", "#353844")
ONDA_SPENTA = ("#C9CBD6", "#3A3D4A")


def colore(c):
    """Sceglie la variante chiara/scura di un colore (serve al disegno della forma d'onda)."""
    if isinstance(c, tuple):
        return c[1] if ctk.get_appearance_mode() == "Dark" else c[0]
    return c


def risorsa(nome):
    """Percorso di un file incluso nell'app (es. l'icona), sia da codice sia nell'.exe."""
    cartella_sorgente = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(getattr(sys, "_MEIPASS", cartella_sorgente), nome)


def font(dimensione=13, grassetto=False):
    return ctk.CTkFont(size=dimensione, weight="bold" if grassetto else "normal")


class Card(ctk.CTkFrame):
    """Riquadro con angoli arrotondati e titolo facoltativo."""

    def __init__(self, master, titolo=None, **kw):
        super().__init__(master, fg_color=SFONDO_CARD, corner_radius=16, **kw)
        if titolo:
            ctk.CTkLabel(self, text=titolo, font=font(15, True), anchor="w").pack(
                fill="x", padx=20, pady=(16, 6))


def bottone_viola(master, testo, comando, **kw):
    return ctk.CTkButton(master, text=testo, command=comando, fg_color=VIOLA,
                         hover_color=VIOLA_HOVER, **kw)


def bottone_neutro(master, testo, comando, **kw):
    return ctk.CTkButton(master, text=testo, command=comando, fg_color=NEUTRO,
                         text_color=TESTO, hover_color=NEUTRO_HOVER, **kw)


def cursore(master, da, a, passi, comando):
    return ctk.CTkSlider(master, from_=da, to=a, number_of_steps=passi, button_color=VIOLA,
                         button_hover_color=VIOLA_HOVER, progress_color=VIOLA, command=comando)


def scelta(master, valori, comando=None, **kw):
    """Pulsanti a scelta singola (es. MP3 / WAV / FLAC)."""
    return ctk.CTkSegmentedButton(master, values=valori, command=comando, selected_color=VIOLA,
                                  selected_hover_color=VIOLA_HOVER, unselected_color=NEUTRO,
                                  unselected_hover_color=NEUTRO_HOVER, text_color=TESTO, **kw)


def etichetta_tenue(master, testo="", dimensione=13, **kw):
    return ctk.CTkLabel(master, text=testo, text_color=TESTO_TENUE, font=font(dimensione), **kw)
