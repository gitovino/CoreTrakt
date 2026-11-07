@echo off
   echo Bezig met compileren van ConeTrakt...
   python -m PyInstaller --noconsole --onefile --collect-all customtkinter --collect-all babelfish --collect-all guessit --icon=app_icon.ico --name "VLC_Trakt_Scrobbler" vlc_trakt_tray.py
   echo.
   echo Bouwen voltooid! De .exe staat in de map 'dist'.
   pause