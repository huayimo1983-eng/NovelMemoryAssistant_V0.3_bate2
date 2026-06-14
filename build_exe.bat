@echo off
chcp 65001 >nul
echo Building NovelMemoryAssistant V0.3 beta...
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --name NovelMemoryAssistant_V0_3_BETA --paths . --collect-submodules app app/main.py
echo Done. Check dist folder.
pause
