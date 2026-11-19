@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno Python. Consulte docs\getting_started.md.
  pause
  exit /b 1
)
echo PyFAST local: abra http://127.0.0.1:8765 en Chrome.
echo Mantenga esta ventana abierta. Ctrl+C cierra el servidor.
".venv\Scripts\python.exe" -m pyfast.web --host 127.0.0.1 --port 8765 --output runs/gui
