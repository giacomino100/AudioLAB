"""Testi e formati mostrati all'utente."""

NOMI_INTERVALLI = {
    0: "tonalità originale", 1: "mezzo tono", 2: "un tono", 3: "un tono e mezzo",
    4: "due toni", 5: "due toni e mezzo", 6: "tre toni", 7: "una quinta",
    8: "una sesta minore", 9: "una sesta", 10: "una settima minore",
    11: "una settima", 12: "un'ottava",
}

FILTRO_FILE = [
    ("Audio e video", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.aiff *.wma "
                      "*.mp4 *.mov *.avi *.mkv *.webm *.m4v *.wmv"),
    ("Tutti i file", "*.*"),
]

FORMATI_AUDIO = {
    "MP3": "320 kbps",
    "WAV": "44,1 kHz senza perdita",
    "FLAC": "senza perdita, compresso",
}


def descrivi_semitoni(semitoni):
    """-2 → "un tono sotto"; 7 → "una quinta sopra · potrebbe suonare meno naturale"."""
    testo = NOMI_INTERVALLI[abs(semitoni)]
    if semitoni:
        testo = f"{testo} {'sopra' if semitoni > 0 else 'sotto'}"
        if abs(semitoni) >= 5:
            testo += " · potrebbe suonare meno naturale"
    return testo


def nome_file_uscita(opzioni, tipo, estensione):
    """Nome proposto quando si salva, es. "Canzone - base (-2) (90%).mp3"."""
    import os

    nome = os.path.splitext(os.path.basename(opzioni.file))[0]
    suffisso = ""
    if opzioni.semitoni:
        suffisso += f" ({opzioni.semitoni:+d})"
    if abs(opzioni.velocita - 1) > 1e-3:
        suffisso += f" ({int(round(opzioni.velocita * 100))}%)"
    if tipo == "Video":
        return f"{nome} - karaoke{suffisso}.mp4"
    if tipo == "Voce":
        etichetta = "voce"
    else:
        etichetta = "base" if opzioni.togli_voce else "modificata"
    return f"{nome} - {etichetta}{suffisso}.{estensione}"
