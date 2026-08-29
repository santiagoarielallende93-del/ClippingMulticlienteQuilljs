@echo off
echo ==========================================
echo Instalando dependencias necesarias...
echo ==========================================
pip install nicegui playwright beautifulsoup4 pandas lxml requests
echo Instalando navegadores de Playwright...
python -m playwright install chromium
echo ==========================================
echo Levantando servidor NiceGUI...
echo ==========================================
python main.py
pause