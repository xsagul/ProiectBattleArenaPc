@echo off
rem The 13.3 client without its packer, connected to our local test server (tools\sponge\lnp_server.py).
rem The match is the 13.3 replay's match; you are player slot 1 = Darius: right click moves him, Ctrl+Q levels Q, Q casts.
rem Close the game window to stop; the server window closes by itself a few seconds later (or close it).
set G=C:\Users\Sorin\Desktop\lol13.3
set P=%~dp0
start "BattleArena 13.3 server" /min cmd /c python "%P%tools\sponge\lnp_server.py" --replay-574 --slot 1 --hero 4000001e --stream "%P%research\rofl\KR-6363178603_13.3.rofl" 5119
timeout /t 2 /nobreak >nul
cd /d "%G%"
start "" /wait "%G%\League of Legends.unpacked.exe" "127.0.0.1 5119 17BLOhi6KZsTtldTsizvHg== 1" -Product=LoL -PlayerID=1 -GameID=1 "-GameBaseDir=%G%" -Region=EUW -PlatformID=EUW1 -Locale=en_US -SkipBuild -UseDX11=1:1
taskkill /F /FI "WINDOWTITLE eq BattleArena 13.3 server*" >nul 2>&1
