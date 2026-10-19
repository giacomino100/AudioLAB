"""La finestra principale: mette insieme i due pannelli e gestisce i lavori lunghi.

I lavori lunghi (elaborazione e salvataggio) girano in un thread separato, così la finestra
resta reattiva. Il thread non tocca mai la finestra direttamente: manda messaggi in una coda,
che la finestra legge ogni 60 millisecondi (_leggi_messaggi).

Messaggi possibili: ("stato", testo, frazione) · ("fatto", Risultato) · ("salvato", percorso)
                    ("annullato",) · ("errore", testo)
"""

import os
import queue
import subprocess
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from karaoke.audio.file_audio import durata_file, e_un_video, salva_audio
from karaoke.audio.video import esporta_video
from karaoke.elaborazione import Elaboratore
from karaoke.interfaccia.pannello_impostazioni import PannelloImpostazioni
from karaoke.interfaccia.pannello_risultato import PannelloRisultato
from karaoke.interfaccia.stile import SFONDO, risorsa
from karaoke.interfaccia.testi import FILTRO_FILE, nome_file_uscita

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:  # il trascinamento è un di più: senza, l'app funziona lo stesso
    TkinterDnD = None

_ClassiBase = (ctk.CTk, TkinterDnD.DnDWrapper) if TkinterDnD else (ctk.CTk,)


class Finestra(*_ClassiBase):
    def __init__(self):
        super().__init__()
        self.trascinamento = self._attiva_trascinamento()
        ctk.set_appearance_mode("dark")
        self.title("Karaoke Studio")
        self.geometry("1120x780")
        self.minsize(980, 700)
        self.configure(fg_color=SFONDO)
        try:
            self.iconbitmap(risorsa("icona.ico"))
        except Exception:
            pass

        self.file = None                 # file scelto dall'utente
        self.cartella_salvataggi = None  # dove è stato salvato l'ultimo file
        self.elaboratore = Elaboratore()
        self.messaggi = queue.Queue()
        self.lavoro = None               # thread in corso (elaborazione o salvataggio)
        self.annulla = False             # messo a True dal pulsante "Annulla"

        # due colonne: impostazioni (larghezza fissa) e risultato (si allarga)
        self.grid_columnconfigure(0, weight=0, minsize=470)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.impostazioni = PannelloImpostazioni(
            self, self.trascinamento, al_scegli_file=self.scegli_file,
            al_elabora=self.elabora_o_annulla, al_cambio_tema=self._cambia_tema)
        self.impostazioni.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        self.risultato = PannelloRisultato(self, al_salva=self.salva,
                                           al_apri_cartella=self.apri_cartella)
        self.risultato.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)

        if self.trascinamento:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._file_trascinato)
        self.bind("<space>", lambda e: self.risultato.play_pausa())
        self.protocol("WM_DELETE_WINDOW", self.chiudi)
        self._timer = self.after(60, self._leggi_messaggi)

    def _attiva_trascinamento(self):
        if not TkinterDnD:
            return False
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            return True
        except Exception:
            return False

    def chiudi(self):
        self.annulla = True
        self.risultato.lettore.ferma()
        self.after_cancel(self._timer)
        self.quit()
        self.destroy()

    def _cambia_tema(self, scelta):
        ctk.set_appearance_mode("dark" if scelta == "Scuro" else "light")
        self.after(50, self.risultato.ridisegna)

    def _occupato(self):
        return self.lavoro is not None and self.lavoro.is_alive()

    # ------------------------------------------------------------ scelta del file
    def _file_trascinato(self, evento):
        file = self.tk.splitlist(evento.data)
        if file:
            self.apri_file(file[0])

    def scegli_file(self):
        if self._occupato():
            return
        percorso = filedialog.askopenfilename(title="Scegli una canzone o un video",
                                              filetypes=FILTRO_FILE)
        if percorso:
            self.apri_file(percorso)

    def apri_file(self, percorso):
        if self._occupato():
            messagebox.showinfo("Karaoke Studio", "Aspetta che finisca l'elaborazione in corso.")
            return
        try:
            durata = durata_file(percorso)
        except Exception as errore:
            messagebox.showerror("Karaoke Studio", f"Impossibile leggere il file:\n{errore}")
            return
        self.file = percorso
        self.impostazioni.mostra_file(percorso, durata, e_un_video(percorso))
        self.risultato.nascondi()

    # ------------------------------------------------------------ elaborazione
    def elabora_o_annulla(self):
        if self._occupato():
            self.annulla = True
            self.impostazioni.mostra_stato("Annullamento…")
            return
        if not self.file:
            messagebox.showinfo("Karaoke Studio", "Scegli prima una canzone o un video.")
            return
        self.risultato.lettore.ferma()
        opzioni = self.impostazioni.opzioni(self.file)
        self._in_background(self._elabora, opzioni, testo_bottone="✕  Annulla")

    def _elabora(self, opzioni):
        """Gira nel thread: esegue la ricetta di elaborazione.py e manda messaggi."""
        try:
            risultato = self.elaboratore.elabora(
                opzioni,
                avanzamento=lambda testo, frazione: self.messaggi.put(("stato", testo, frazione)),
                interrompi=lambda: self.annulla)
            self.messaggi.put(("fatto", risultato))
        except InterruptedError:
            self.messaggi.put(("annullato",))
        except Exception as errore:
            self.messaggi.put(("errore", str(errore)))

    # ------------------------------------------------------------ salvataggio
    def salva(self, tipo):
        """tipo: "Base", "Voce" o "Video". Chiede dove salvare, poi salva in background."""
        risultato = self.risultato.risultato
        if risultato is None or self._occupato():
            return
        estensione = "mp4" if tipo == "Video" else self.risultato.formato_scelto()
        nome = nome_file_uscita(risultato.opzioni, tipo, estensione)
        filtro = [("Video MP4", "*.mp4")] if tipo == "Video" else [(estensione.upper(),
                                                                   "*." + estensione)]
        percorso = filedialog.asksaveasfilename(
            title=f"Salva {tipo.lower()}", initialdir=os.path.dirname(self.file),
            initialfile=nome, defaultextension="." + estensione, filetypes=filtro)
        if percorso:
            self.risultato.lettore.ferma()
            self._in_background(self._salva, (tipo, percorso), testo_bottone="▶  Elabora")

    def _salva(self, richiesta):
        """Gira nel thread: salva la traccia così come la si sente (con l'equalizzatore)."""
        tipo, percorso = richiesta
        try:
            if tipo == "Video":
                self.messaggi.put(("stato", "Creo il video karaoke…", 0.5))
                opzioni = self.risultato.risultato.opzioni
                esporta_video(opzioni.file, self.risultato.tracce["Base"], percorso,
                              opzioni.velocita)
            else:
                self.messaggi.put(("stato", f"Salvo {os.path.basename(percorso)}…", 0.5))
                salva_audio(percorso, self.risultato.tracce[tipo])
            self.messaggi.put(("salvato", percorso))
        except Exception as errore:
            self.messaggi.put(("errore", str(errore)))

    def apri_cartella(self):
        cartella = self.cartella_salvataggi or (os.path.dirname(self.file) if self.file else None)
        if cartella:
            subprocess.Popen(["explorer", os.path.normpath(cartella)])

    # ------------------------------------------------------------ lavori in background
    def _in_background(self, funzione, argomento, testo_bottone):
        self.annulla = False
        self.impostazioni.modalita_lavoro(True, testo_bottone)
        self.risultato.abilita_salvataggio(False)
        self.lavoro = threading.Thread(target=funzione, args=(argomento,), daemon=True)
        self.lavoro.start()

    def _leggi_messaggi(self):
        """Ogni 60 ms: legge i messaggi del thread e aggiorna la finestra."""
        try:
            while True:
                self.gestisci_messaggio(self.messaggi.get_nowait())
        except queue.Empty:
            pass
        self.risultato.aggiorna()
        self._timer = self.after(60, self._leggi_messaggi)

    def gestisci_messaggio(self, messaggio):
        tipo = messaggio[0]
        if tipo == "stato":
            self.impostazioni.mostra_stato(messaggio[1], messaggio[2])
            return
        # tutti gli altri messaggi segnano la fine del lavoro
        self.impostazioni.modalita_lavoro(False)
        self.risultato.abilita_salvataggio(True)
        if tipo == "fatto":
            self.impostazioni.mostra_stato(
                "✓ Fatto! Ascolta l'anteprima e salva quello che ti serve", 1.0)
            self.risultato.mostra(messaggio[1])
        elif tipo == "salvato":
            self.cartella_salvataggi = os.path.dirname(messaggio[1])
            self.impostazioni.mostra_stato("✓ Salvato", 1.0)
            self.risultato.mostra_salvato(os.path.basename(messaggio[1]))
        elif tipo == "annullato":
            self.impostazioni.mostra_stato("Operazione annullata", 0)
        else:
            self.impostazioni.mostra_stato("Errore", 0)
            messagebox.showerror("Karaoke Studio", messaggio[1])
