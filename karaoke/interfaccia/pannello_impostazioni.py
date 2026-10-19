"""Colonna sinistra: scelta del file, voce, volume, tonalità, velocità e pulsante "Elabora".

Il pannello raccoglie le scelte dell'utente e le consegna come Opzioni (vedi elaborazione.py).
Non avvia nessun lavoro: quando si preme un pulsante chiama le funzioni della finestra.
"""

import os

import customtkinter as ctk

from karaoke import impostazioni
from karaoke.audio.separazione_demucs import demucs_disponibile
from karaoke.elaborazione import Opzioni, formatta_durata
from karaoke.interfaccia.stile import (BORDO, ROSSO, ROSSO_HOVER, SFONDO_CARD, TESTO_TENUE,
                                       VIOLA, VIOLA_HOVER, Card, bottone_neutro, cursore,
                                       etichetta_tenue, font, scelta)
from karaoke.interfaccia.testi import descrivi_semitoni


class PannelloImpostazioni(ctk.CTkScrollableFrame):
    def __init__(self, master, trascinamento, al_scegli_file, al_elabora, al_cambio_tema):
        super().__init__(master, fg_color="transparent", width=450)
        self.al_scegli_file = al_scegli_file
        self.durata_file = None
        self.occupato = False        # True mentre è in corso un'elaborazione o un salvataggio

        self._crea_intestazione(al_cambio_tema)
        self._crea_zona_file(trascinamento)
        self._crea_card_voce()
        self._crea_card_tonalita()
        self._crea_elabora(al_elabora)
        self._aggiorna_stima()

    # ------------------------------------------------------------ costruzione
    def _crea_intestazione(self, al_cambio_tema):
        testa = ctk.CTkFrame(self, fg_color="transparent")
        testa.pack(fill="x", padx=8, pady=(4, 12))
        ctk.CTkLabel(testa, text="🎤  Karaoke Studio", font=font(26, True), anchor="w").pack(fill="x")
        etichetta_tenue(testa, "Togli la voce da canzoni e video", anchor="w").pack(fill="x")
        self.tema = scelta(testa, ["Scuro", "Chiaro"], al_cambio_tema)
        self.tema.set("Scuro")
        self.tema.place(relx=1.0, rely=0.0, anchor="ne")

    def _crea_zona_file(self, trascinamento):
        """Il riquadro dove si trascina o si sceglie il file."""
        self.zona = ctk.CTkFrame(self, fg_color=SFONDO_CARD, corner_radius=16, border_width=2,
                                 border_color=BORDO, height=150)
        self.zona.pack(fill="x", padx=8, pady=6)
        self.zona_icona = ctk.CTkLabel(self.zona, text="⬆", font=font(30), text_color=VIOLA)
        self.zona_icona.pack(pady=(18, 0))
        self.zona_titolo = ctk.CTkLabel(
            self.zona, font=font(15, True),
            text="Trascina qui un audio o un video" if trascinamento
            else "Clicca per scegliere un file")
        self.zona_titolo.pack()
        self.zona_sotto = etichetta_tenue(
            self.zona, ("oppure clicca per sceglierlo · " if trascinamento else "")
            + "MP3, WAV, FLAC, M4A, MP4, MOV, AVI, MKV, WebM")
        self.zona_sotto.pack(pady=(0, 18))
        for elemento in (self.zona, self.zona_icona, self.zona_titolo, self.zona_sotto):
            elemento.bind("<Button-1>", lambda e: self.al_scegli_file())
            elemento.configure(cursor="hand2")

    def _crea_card_voce(self):
        card = Card(self, "Voce")
        card.pack(fill="x", padx=8, pady=6)

        self.togli_voce = ctk.CTkSwitch(card, text="Togli la voce", progress_color=VIOLA,
                                        command=self._attiva_opzioni_voce)
        self.togli_voce.select()
        self.togli_voce.pack(anchor="w", padx=20, pady=4)

        etichetta_tenue(card, "Motore IA", anchor="w").pack(fill="x", padx=20, pady=(8, 0))
        # senza PyTorch (es. Smart App Control attivo) resta solo MDX-Net
        motori = list(impostazioni.MOTORI) if demucs_disponibile() else ["MDX-Net"]
        self.motore = scelta(card, motori, lambda v: self._aggiorna_stima())
        self.motore.set(impostazioni.MOTORE_PREDEFINITO
                        if impostazioni.MOTORE_PREDEFINITO in motori else motori[0])
        self.motore.pack(anchor="w", padx=20, pady=(2, 2))
        self.motore_descrizione = etichetta_tenue(card, dimensione=11, anchor="w")
        self.motore_descrizione.pack(fill="x", padx=20)

        etichetta_tenue(card, "Volume uniforme", anchor="w").pack(fill="x", padx=20, pady=(8, 0))
        self.volume = scelta(card, list(impostazioni.VOLUME_UNIFORME), self._descrivi_volume)
        self.volume.set(impostazioni.VOLUME_PREDEFINITO)
        self.volume.pack(anchor="w", padx=20, pady=(2, 2))
        self.volume_descrizione = etichetta_tenue(card, dimensione=11, anchor="w")
        self.volume_descrizione.pack(fill="x", padx=20)
        self._descrivi_volume(impostazioni.VOLUME_PREDEFINITO)

        self.qualita_extra = ctk.CTkCheckBox(
            card, text="Qualità extra (più pulita, ma impiega il doppio)", fg_color=VIOLA,
            hover_color=VIOLA_HOVER, command=self._aggiorna_stima)
        self.qualita_extra.pack(anchor="w", padx=20, pady=(10, 18))

    def _crea_card_tonalita(self):
        card = Card(self, "Tonalità e velocità")
        card.pack(fill="x", padx=8, pady=6)

        riga = ctk.CTkFrame(card, fg_color="transparent")
        riga.pack(fill="x", padx=20)
        bottone_neutro(riga, "−", lambda: self._passo_semitoni(-1), width=40, height=40,
                       font=font(20)).pack(side="left")
        centro = ctk.CTkFrame(riga, fg_color="transparent")
        centro.pack(side="left", fill="x", expand=True)
        self.semitoni_valore = ctk.CTkLabel(centro, text="0", font=font(30, True))
        self.semitoni_valore.pack()
        self.semitoni_descrizione = etichetta_tenue(centro, "tonalità originale")
        self.semitoni_descrizione.pack()
        bottone_neutro(riga, "+", lambda: self._passo_semitoni(1), width=40, height=40,
                       font=font(20)).pack(side="left")
        massimo = impostazioni.SEMITONI_MAX
        self.semitoni = cursore(card, -massimo, massimo, 2 * massimo, self._descrivi_semitoni)
        self.semitoni.set(0)
        self.semitoni.pack(fill="x", padx=20, pady=(10, 2))

        riga_vel = ctk.CTkFrame(card, fg_color="transparent")
        riga_vel.pack(fill="x", padx=20, pady=(12, 0))
        ctk.CTkLabel(riga_vel, text="Velocità").pack(side="left")
        self.velocita_valore = ctk.CTkLabel(riga_vel, text="100%", font=font(13, True))
        self.velocita_valore.pack(side="right")
        minimo, massimo = impostazioni.VELOCITA_MIN, impostazioni.VELOCITA_MAX
        self.velocita = cursore(card, minimo, massimo, (massimo - minimo) // 5,
                                lambda v: self.velocita_valore.configure(text=f"{int(v)}%"))
        self.velocita.set(100)
        self.velocita.pack(fill="x", padx=20, pady=(4, 18))

    def _crea_elabora(self, al_elabora):
        self.bottone_elabora = ctk.CTkButton(self, text="▶  Elabora", height=52, corner_radius=14,
                                             font=font(17, True), fg_color=VIOLA,
                                             hover_color=VIOLA_HOVER, command=al_elabora)
        self.bottone_elabora.pack(fill="x", padx=8, pady=(12, 8))
        self.barra = ctk.CTkProgressBar(self, progress_color=VIOLA, height=10)
        self.barra.set(0)
        self.barra.pack(fill="x", padx=8, pady=4)
        self.stato = ctk.CTkLabel(self, text="Scegli una canzone o un video per iniziare",
                                  text_color=TESTO_TENUE, wraplength=420)
        self.stato.pack(padx=8, pady=(0, 6))

    # ------------------------------------------------------------ reazioni ai comandi
    def _attiva_opzioni_voce(self):
        stato = "normal" if self.togli_voce.get() else "disabled"
        for elemento in (self.motore, self.volume, self.qualita_extra):
            elemento.configure(state=stato)

    def _descrivi_volume(self, nome):
        self.volume_descrizione.configure(text=impostazioni.DESCRIZIONI_VOLUME[nome])

    def _passo_semitoni(self, passo):
        massimo = impostazioni.SEMITONI_MAX
        valore = max(-massimo, min(massimo, int(round(self.semitoni.get())) + passo))
        self.semitoni.set(valore)
        self._descrivi_semitoni(valore)

    def _descrivi_semitoni(self, valore):
        valore = int(round(valore))
        self.semitoni_valore.configure(text=f"{valore:+d}" if valore else "0")
        self.semitoni_descrizione.configure(text=descrivi_semitoni(valore))

    def _aggiorna_stima(self):
        descrizione, minuti_per_minuto = impostazioni.MOTORI[self.motore.get()]
        self.motore_descrizione.configure(text=descrizione)
        if self.durata_file is not None and not self.occupato:
            stima = self.durata_file / 60 * minuti_per_minuto * (2 if self.qualita_extra.get() else 1)
            self.stato.configure(text=f"Pronto · separazione stimata ~{max(1, round(stima))} min")

    # ------------------------------------------------------------ usati dalla finestra
    def mostra_file(self, percorso, durata, video):
        self.durata_file = durata
        self.zona_icona.configure(text="🎬" if video else "🎵")
        self.zona_titolo.configure(text=os.path.basename(percorso))
        self.zona_sotto.configure(text=f"{'Video' if video else 'Audio'} · {formatta_durata(durata)}"
                                       " · clicca o trascina per cambiare")
        self.barra.set(0)
        self._aggiorna_stima()

    def opzioni(self, file):
        """Le scelte attuali dell'utente."""
        return Opzioni(
            file=file,
            togli_voce=bool(self.togli_voce.get()),
            motore=self.motore.get(),
            qualita_extra=bool(self.qualita_extra.get()),
            volume_uniforme=impostazioni.VOLUME_UNIFORME[self.volume.get()],
            semitoni=int(round(self.semitoni.get())),
            velocita=self.velocita.get() / 100,
        )

    def mostra_stato(self, testo=None, avanzamento=None):
        if testo is not None:
            self.stato.configure(text=testo)
        if avanzamento is not None:
            self.barra.set(avanzamento)

    def modalita_lavoro(self, attiva, testo_bottone="✕  Annulla"):
        """Durante un lavoro il pulsante diventa rosso e serve ad annullare."""
        self.occupato = attiva
        if attiva:
            self.bottone_elabora.configure(text=testo_bottone, fg_color=ROSSO,
                                           hover_color=ROSSO_HOVER)
        else:
            self.bottone_elabora.configure(text="▶  Elabora", fg_color=VIOLA,
                                           hover_color=VIOLA_HOVER)
