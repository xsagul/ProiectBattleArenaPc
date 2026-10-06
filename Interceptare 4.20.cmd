@echo off
rem Starts the 4.20 sandbox with the interceptor in the middle: LeagueSandbox on UDP 5129, tools\lol420_proxy.py on
rem 5119 (where the original client connects), then the client. Every packet is recorded in research\lol420_capture.
title Interceptare 4.20
setlocal enabledelayedexpansion
set "ROOT=%~dp0"
set "SANDBOX=C:\Users\Sorin\Desktop\4.20"
set "SERVER_DIR=%SANDBOX%\GameServer\GameServerConsole\bin\Debug\net8.0"
set "CLIENT_DIR=%SANDBOX%\Client\League-of-Legends-4-20\RADS\solutions\lol_game_client_sln\releases\0.0.1.68\deploy"

echo [1/4] Oprire instante vechi...
taskkill /F /IM "League of Legends.exe" >nul 2>&1
taskkill /F /IM dotnet.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [2/4] Server LeagueSandbox pe portul 5129...
start "LeagueSandbox 5129" cmd /k "cd /d "%SERVER_DIR%" && dotnet GameServerConsole.dll --port 5129"

echo [3/4] Interceptor pe portul 5119...
start "Interceptor 4.20" cmd /k "python "%ROOT%tools\lol420_proxy.py" --listen 5119 --server 5129"

echo Astept serverul...
set READY=0
for /L %%i in (1,1,30) do (
  if "!READY!"=="0" (
    netstat -ano | findstr ":5129 " >nul && set READY=1
    timeout /t 1 /nobreak >nul
  )
)
timeout /t 3 /nobreak >nul

echo [4/4] Pornire client 4.20...
cd /d "%CLIENT_DIR%"
start "" "League of Legends.exe" "8394" "LoLLauncher.exe" "" "127.0.0.1 5119 17BLOhi6KZsTtldTsizvHg== 1"
echo.
echo Joaca normal (miscare, abilitati, click pe minimapa, shop). Cand termini, inchide jocul
echo si fereastra "Interceptor 4.20". Inregistrarea e in research\lol420_capture.
pause
