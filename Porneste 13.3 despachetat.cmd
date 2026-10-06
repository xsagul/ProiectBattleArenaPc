@echo off
rem The 13.3 client without its packer (assembled by tools\sponge\build_unpacked.py, started by our ba_host.dll),
rem playing the 13.3 replay. Same window and controls as the original client's replay mode.
set G=C:\Users\Sorin\Desktop\lol13.3
cd /d "%G%"
start "" "%G%\League of Legends.unpacked.exe" "%~dp0research\rofl\KR-6363178603_13.3.rofl" "-GameBaseDir=%G%" -SkipRads -SkipBuild -EnableLNP -UseDX11=1:1 -Locale=en_US
