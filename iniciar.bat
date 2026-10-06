@echo off
set PLAYWRIGHT_BROWSERS_PATH=0
echo ==========================================
echo Instalando dependencias necesarias...
echo ==========================================
python -m pip install nicegui playwright beautifulsoup4 pandas lxml requests PyMuPDF
echo Instalando navegadores de Playwright...
python -m playwright install chromium
echo ==========================================
echo Levantando servidor NiceGUI...
echo ==========================================
python main.py
pause
