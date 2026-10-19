"""La forma d'onda dell'anteprima: si clicca per spostarsi, la parte ascoltata è colorata."""

import customtkinter as ctk
import numpy as np

from karaoke.interfaccia.stile import ONDA_SPENTA, SFONDO_CARD, VIOLA, colore


class FormaOnda(ctk.CTkCanvas):
    LARGHEZZA_BARRA = 3
    SPAZIO = 1

    def __init__(self, master, al_click, **kw):
        """al_click(frazione 0..1) viene chiamata quando l'utente clicca o trascina."""
        super().__init__(master, height=110, highlightthickness=0, bd=0, **kw)
        self.al_click = al_click
        self.audio = None
        self.barre = []
        self.colorate = 0
        self.bind("<Configure>", lambda e: self.disegna())
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._click)

    def _click(self, evento):
        if self.barre:
            self.al_click(evento.x / max(1, self.winfo_width()))

    def imposta(self, audio):
        """audio: (campioni, 2), come nel Lettore."""
        self.audio = audio
        self.disegna()

    def disegna(self):
        self.delete("all")
        self.configure(bg=colore(SFONDO_CARD))
        self.barre = []
        self.colorate = 0
        larghezza, altezza = self.winfo_width(), self.winfo_height()
        if self.audio is None or larghezza < 10:
            return
        passo = self.LARGHEZZA_BARRA + self.SPAZIO
        n_barre = max(1, larghezza // passo)
        mono = np.abs(self.audio).max(axis=1)
        per_barra = len(mono) // n_barre
        if per_barra < 1:
            return
        picchi = mono[:per_barra * n_barre].reshape(n_barre, per_barra).max(axis=1)
        picchi = picchi / (picchi.max() + 1e-9)
        spenta = colore(ONDA_SPENTA)
        for i, p in enumerate(picchi):
            alta = max(2, p * (altezza - 10))
            x = i * passo
            self.barre.append(self.create_rectangle(
                x, (altezza - alta) / 2, x + self.LARGHEZZA_BARRA, (altezza + alta) / 2,
                fill=spenta, width=0))

    def avanzamento(self, frazione):
        """Colora le barre fino al punto di ascolto (ricolora solo quelle cambiate)."""
        if not self.barre:
            return
        nuove = int(frazione * len(self.barre))
        if nuove == self.colorate:
            return
        da, a = sorted((self.colorate, nuove))
        col = VIOLA if nuove > self.colorate else colore(ONDA_SPENTA)
        for barra in self.barre[da:a]:
            self.itemconfigure(barra, fill=col)
        self.colorate = nuove
