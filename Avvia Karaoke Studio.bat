@echo off
chcp 65001 >nul
set "V=%LOCALAPPDATA%\KaraokeStudio\venv"
if not exist "%V%\Scripts\pythonw.exe" (
  echo Prima installazione di Karaoke Studio: qualche minuto di pazienza...
  python -m venv "%V%" || (echo Python non trovato. Installalo da python.org & pause & exit /b 1)
  "%V%\Scripts\python.exe" -m pip install --upgrade pip
  "%V%\Scripts\python.exe" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  "%V%\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt" || (echo Installazione non riuscita & pause & exit /b 1)
)
start "" "%V%\Scripts\pythonw.exe" "%~dp0karaoke_studio.py"
