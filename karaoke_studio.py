"""Avvio di Karaoke Studio.

    python karaoke_studio.py                       apre l'app
    python karaoke_studio.py --autotest <cartella> prova automatica (vedi karaoke/autotest.py)

Il codice vero e proprio è nella cartella karaoke/ (vedi STRUTTURA.md).
"""

import os
import sys

# Nell'.exe senza console stdout/stderr non esistono e le librerie che scrivono messaggi
# andrebbero in errore: li mandiamo nel "nulla".
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--autotest":
        from karaoke import autotest
        autotest.esegui(sys.argv[2])
    else:
        from karaoke.interfaccia.finestra import Finestra
        Finestra().mainloop()


if __name__ == "__main__":
    main()
