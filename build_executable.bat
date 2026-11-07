@echo off
echo Bezig met compileren van CoreTrakt...
python -m PyInstaller --noconsole --onefile --collect-all customtkinter --collect-all babelfish --collect-all guessit --icon=app_icon.ico --name "CoreTrakt" vlc_trakt_tray.py
echo.
echo Bouwen voltooid! CoreTrakt.exe staat in de map 'dist'.
pause