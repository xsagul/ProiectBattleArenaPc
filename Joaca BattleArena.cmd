@echo off
rem BattleArena: starts the lobby (it opens in the browser). Close this window to quit.
cd /d "%~dp0build-clang\bin"
"%~dp0build-clang\bin\lobby.exe"
