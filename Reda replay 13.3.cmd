@echo off
rem BattleArena: our client plays Riot's 13.3 replay (the server's own packets, research\exe133\replay_13.3.barp).
rem Starts at second 60 (the first minion wave leaves at 65). Arrow keys move the camera.
rem Another moment: add the second to start from, e.g.   "Reda replay 13.3.cmd" 300
set START=%1
if "%START%"=="" set START=60
cd /d "%~dp0build-clang\bin"
"%~dp0build-clang\bin\client.exe" --replay "%~dp0research\exe133\replay_13.3.barp" --offline-start %START% --cam-x 7400 --cam-z 7400 --zoom 2200
