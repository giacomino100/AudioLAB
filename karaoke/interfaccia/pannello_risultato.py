"""Colonna destra: anteprima del risultato, equalizzatore della base e salvataggio.

Prima dell'elaborazione mostra un riquadro vuoto ("Qui ascolterai il risultato").
L'equalizzatore lavora in un thread a parte: muovendo i cursori l'ascolto non si ferma.
"""

import queue
import threading
from tkinter import messagebox

import customtkinter as ctk

from karaoke import impostazioni
from karaoke.audio.equalizzatore import equalizza
from karaoke.audio.file_audio import e_un_video
from karaoke.elaborazione import formatta_durata
from karaoke.interfaccia.forma_onda import FormaOnda
from karaoke.interfaccia.lettore import Lettore
from karaoke.interfaccia.stile import (VERDE, VERDE_HOVER, Card, bottone_neutro, bottone_viola,
                                       cursore, etichetta_tenue, font, scelta)
from karaoke.interfaccia.testi import FORMATI_AUDIO

EQ_SPENTO = {"bassi": 0.0, "medi": 0.0, "alti": 0.0}


class PannelloRisultato(ctk.CTkScrollableFrame):
    def __init__(self, master, al_salva, al_apri_cartella):
        """al_salva(tipo) con tipo "Base", "Voce" o "Video"."""
        super().__init__(master, fg_color="transparent")
        self.risultato = None
        self.tracce = {}               # ciò che si ascolta e si salva (Base con l'equalizzatore)
        self.lettore = Lettore()

        # equalizzatore: ricalcolo in un thread, risultato consegnato tramite questa coda
        self._eq_coda = queue.Queue()
        self._eq_timer = None
        self._eq_in_corso = False
        self._eq_da_rifare = False

        self._crea_riquadro_vuoto()
        self.contenuto = ctk.CTkFrame(self, fg_color="transparent")
        self._crea_anteprima()
        self._crea_equalizzatore()
        self._crea_salvataggio(al_salva, al_apri_cartella)

    # ------------------------------------------------------------ costruzione
    def _crea_riquadro_vuoto(self):
        self.vuoto = Card(self, height=640)
        self.vuoto.pack_propagate(False)
        self.vuoto.pack(fill="both", expand=True)
        ctk.CTkLabel(self.vuoto, text="🎧", font=font(48)).pack(pady=(160, 6))
        ctk.CTkLabel(self.vuoto, text="Qui ascolterai il risultato", font=font(17, True)).pack()
        etichetta_tenue(self.vuoto, "Potrai confrontare originale, voce e base\n"
                                    "e salvare quello che ti serve.").pack(pady=4)

    def _crea_anteprima(self):
        card = Card(self.contenuto, "Anteprima")
        card.pack(fill="x")
        self.scelta_traccia = scelta(card, ["Originale", "Base", "Voce"], self._scegli_traccia,
                                     font=font(14, True), height=36)
        self.scelta_traccia.pack(fill="x", padx=20, pady=(0, 12))
        self.onda = FormaOnda(card, self._vai)
        self.onda.pack(fill="x", padx=20)
        comandi = ctk.CTkFrame(card, fg_color="transparent")
        comandi.pack(fill="x", padx=20, pady=(10, 18))
        self.bottone_play = bottone_viola(comandi, "▶", self.play_pausa, width=52, height=52,
                                          corner_radius=26, font=font(20))
        self.bottone_play.pack(side="left")
        self.tempo = ctk.CTkLabel(comandi, text="0:00 / 0:00", font=font(14))
        self.tempo.pack(side="left", padx=14)
        self.dettagli = etichetta_tenue(comandi)
        self.dettagli.pack(side="right")

    def _crea_equalizzatore(self):
        card = Card(self.contenuto, "Equalizzatore della base")
        card.pack(fill="x", pady=(12, 0))
        etichetta_tenue(card, "Togliendo la voce i bassi prevalgono e i medi si svuotano. "
                              "«Automatico» riequilibra il suono; poi ritocca a orecchio "
                              "mentre ascolti.", anchor="w", justify="left",
                        wraplength=560).pack(fill="x", padx=20, pady=(0, 8))
        griglia = ctk.CTkFrame(card, fg_color="transparent")
        griglia.pack(fill="x", padx=20)
        griglia.grid_columnconfigure((0, 1, 2), weight=1, uniform="eq")
        self.eq_cursori, self.eq_valori = {}, {}
        bande = (("bassi", "Bassi", "sotto 250 Hz"),
                 ("medi", "Medi", "250 Hz – 4 kHz"),
                 ("alti", "Alti", "sopra 4 kHz"))
        for colonna, (banda, titolo, frequenze) in enumerate(bande):
            box = ctk.CTkFrame(griglia, fg_color="transparent")
            box.grid(row=0, column=colonna, sticky="ew", padx=6)
            testa = ctk.CTkFrame(box, fg_color="transparent")
            testa.pack(fill="x")
            ctk.CTkLabel(testa, text=titolo, font=font(13, True)).pack(side="left")
            self.eq_valori[banda] = ctk.CTkLabel(testa, text="0 dB")
            self.eq_valori[banda].pack(side="right")
            c = cursore(box, -impostazioni.EQ_MAX, impostazioni.EQ_MAX, 48,
                        lambda v, b=banda: self._eq_cursore_mosso(b, v))
            c.set(0)
            c.pack(fill="x", pady=(4, 0))
            etichetta_tenue(box, frequenze, dimensione=11).pack()
            self.eq_cursori[banda] = c
        riga = ctk.CTkFrame(card, fg_color="transparent")
        riga.pack(fill="x", padx=20, pady=(8, 16))
        bottone_viola(riga, "✨  Automatico", self._eq_automatico, width=140).pack(side="left")
        bottone_neutro(riga, "Azzera", self._eq_azzera, width=90).pack(side="left", padx=8)
        self.eq_stato = etichetta_tenue(riga)
        self.eq_stato.pack(side="right")

    def _crea_salvataggio(self, al_salva, al_apri_cartella):
        card = Card(self.contenuto, "Scarica")
        card.pack(fill="x", pady=(12, 0))

        riga_formato = ctk.CTkFrame(card, fg_color="transparent")
        riga_formato.pack(fill="x", padx=20, pady=(0, 10))
        etichetta_tenue(riga_formato, "Formato audio").pack(side="left")
        self.formato = scelta(riga_formato, list(FORMATI_AUDIO),
                              lambda v: self.formato_descrizione.configure(text=FORMATI_AUDIO[v]))
        self.formato.set("MP3")
        self.formato.pack(side="left", padx=12)
        self.formato_descrizione = etichetta_tenue(riga_formato, FORMATI_AUDIO["MP3"])
        self.formato_descrizione.pack(side="left")

        riga_bottoni = ctk.CTkFrame(card, fg_color="transparent")
        riga_bottoni.pack(fill="x", padx=20, pady=(0, 10))
        riga_bottoni.grid_columnconfigure((0, 1), weight=1)
        self.salva_base = bottone_viola(riga_bottoni, "⬇  Salva base", lambda: al_salva("Base"),
                                        height=44, font=font(14, True))
        self.salva_base.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.salva_voce = bottone_neutro(riga_bottoni, "⬇  Salva voce", lambda: al_salva("Voce"),
                                         height=44, font=font(14, True))
        self.salva_voce.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.salva_video = ctk.CTkButton(card, text="🎬  Salva video karaoke (video + base)",
                                         height=44, fg_color=VERDE, hover_color=VERDE_HOVER,
                                         font=font(14, True), command=lambda: al_salva("Video"))
        self.video_nota = etichetta_tenue(card, "Stesse immagini del video originale, con la base "
                                                "al posto dell'audio · salvato in MP4", dimensione=11)

        riga_fondo = ctk.CTkFrame(card, fg_color="transparent")
        riga_fondo.pack(fill="x", padx=20, pady=(4, 16), side="bottom")
        self.ultimo_salvato = etichetta_tenue(riga_fondo, anchor="w", justify="left",
                                              wraplength=420)
        self.ultimo_salvato.pack(side="left", fill="x", expand=True)
        bottone_neutro(riga_fondo, "📂  Apri cartella", al_apri_cartella,
                       width=140).pack(side="right")

    # ------------------------------------------------------------ usati dalla finestra
    def mostra(self, risultato):
        """Mostra un nuovo risultato: carica le tracce e imposta l'equalizzatore automatico."""
        self.risultato = risultato
        self.tracce = risultato.tracce()
        opzioni = risultato.opzioni

        self.vuoto.pack_forget()
        self.contenuto.pack(fill="both", expand=True)
        self.scelta_traccia.configure(values=list(self.tracce))
        self.scelta_traccia.set("Base")
        self.lettore.carica(self.tracce, "Base")
        self.onda.imposta(self.lettore.audio)

        dettagli = []
        if opzioni.togli_voce:
            dettagli.append(opzioni.motore)
        if opzioni.semitoni:
            dettagli.append(f"{opzioni.semitoni:+d} semitoni")
        if abs(opzioni.velocita - 1) > 1e-3:
            dettagli.append(f"velocità {int(round(opzioni.velocita * 100))}%")
        self.dettagli.configure(text=" · ".join(dettagli))

        self.salva_base.configure(text="⬇  Salva base" if opzioni.togli_voce else "⬇  Salva audio")
        if opzioni.togli_voce:
            self.salva_voce.grid()
        else:
            self.salva_voce.grid_remove()
        self.salva_video.pack_forget()
        self.video_nota.pack_forget()
        if e_un_video(opzioni.file):
            self.salva_video.pack(fill="x", padx=20, pady=(0, 4))
            self.video_nota.pack(fill="x", padx=20, pady=(0, 8))
        self.ultimo_salvato.configure(text="")

        self._eq_mostra_valori(risultato.eq)
        self.eq_stato.configure(text="Automatico" if any(risultato.eq.values()) else "")

    def nascondi(self):
        self.lettore.ferma()
        self.risultato = None
        self.tracce = {}
        self.contenuto.pack_forget()
        self.vuoto.pack(fill="both", expand=True)

    def formato_scelto(self):
        return self.formato.get().lower()

    def abilita_salvataggio(self, abilita):
        for bottone in (self.salva_base, self.salva_voce, self.salva_video):
            bottone.configure(state="normal" if abilita else "disabled")

    def mostra_salvato(self, nome_file):
        self.ultimo_salvato.configure(text="✓ " + nome_file)

    def aggiorna(self):
        """Chiamata dalla finestra più volte al secondo: punto di ascolto ed equalizzatore."""
        try:
            while True:
                self._eq_pronto(self._eq_coda.get_nowait())
        except queue.Empty:
            pass
        if self.tracce:
            self.onda.avanzamento(self.lettore.frazione())
            self.tempo.configure(text=f"{formatta_durata(self.lettore.secondi())} / "
                                      f"{formatta_durata(self.lettore.durata())}")
            self.bottone_play.configure(text="❚❚" if self.lettore.in_riproduzione() else "▶")

    def ridisegna(self):
        """Dopo il cambio di tema la forma d'onda va ridisegnata con i nuovi colori."""
        self.onda.disegna()
        self.onda.avanzamento(self.lettore.frazione())

    # ------------------------------------------------------------ anteprima
    def play_pausa(self):
        if not self.tracce:
            return
        if self.lettore.in_riproduzione():
            self.lettore.ferma()
        else:
            self.lettore.suona()

    def _scegli_traccia(self, nome):
        suonava = self.lettore.in_riproduzione()
        self.lettore.ferma()
        self.lettore.scegli(nome)
        self.onda.imposta(self.lettore.audio)
        self.onda.avanzamento(self.lettore.frazione())
        if suonava:
            self.lettore.suona()

    def _vai(self, frazione):
        suonava = self.lettore.in_riproduzione()
        self.lettore.ferma()
        self.lettore.vai(frazione)
        self.onda.avanzamento(self.lettore.frazione())
        if suonava:
            self.lettore.suona()

    # ------------------------------------------------------------ equalizzatore
    def eq_valori_attuali(self):
        return {banda: round(float(c.get()), 1) for banda, c in self.eq_cursori.items()}

    def _eq_mostra_valori(self, valori):
        for banda, valore in valori.items():
            self.eq_cursori[banda].set(valore)
            self.eq_valori[banda].configure(text=f"{valore:+.1f} dB" if valore else "0 dB")

    def _eq_cursore_mosso(self, banda, valore):
        self.eq_valori[banda].configure(text=f"{valore:+.1f} dB" if round(valore, 1) else "0 dB")
        self.eq_stato.configure(text="Personalizzato")
        self._eq_programma()

    def _eq_automatico(self):
        if self.risultato:
            self._eq_mostra_valori(self.risultato.eq)
        self.eq_stato.configure(text="Automatico")
        self._eq_programma()

    def _eq_azzera(self):
        self._eq_mostra_valori(EQ_SPENTO)
        self.eq_stato.configure(text="Spento")
        self._eq_programma()

    def _eq_programma(self):
        """Aspetta 250 ms dall'ultimo movimento dei cursori, poi ricalcola la base."""
        if self.risultato is None:
            return
        if self._eq_timer:
            self.after_cancel(self._eq_timer)
        self._eq_timer = self.after(250, self.eq_ricalcola)

    def eq_ricalcola(self):
        self._eq_timer = None
        if self._eq_in_corso:                 # un calcolo è già in corso: lo si rifà dopo
            self._eq_da_rifare = True
            return
        self._eq_in_corso = True
        valori, base = self.eq_valori_attuali(), self.risultato.base_senza_eq

        def calcola():
            try:
                self._eq_coda.put(equalizza(base, **valori))
            except Exception as errore:
                self._eq_coda.put(errore)

        threading.Thread(target=calcola, daemon=True).start()

    def _eq_pronto(self, audio):
        self._eq_in_corso = False
        if isinstance(audio, Exception):
            messagebox.showerror("Karaoke Studio", f"Equalizzatore: {audio}")
        elif self.tracce:
            # sostituisce la base senza fermare l'ascolto: si sente subito la differenza
            self.tracce["Base"] = audio
            self.lettore.sostituisci("Base", audio)
            if self.lettore.attiva == "Base":
                self.onda.imposta(self.lettore.audio)
                self.onda.avanzamento(self.lettore.frazione())
        if self._eq_da_rifare:
            self._eq_da_rifare = False
            self.eq_ricalcola()
