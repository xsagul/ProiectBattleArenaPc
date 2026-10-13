@echo off
rem BattleArena on the League 16.20 game copy (game16) with our own server (server\main16.py).
rem Opens the out-of-game client page: PLAY -> Summoner's Rift -> Confirm -> Find Match -> Accept -> pick any of the
rem 173 champions -> Lock In. The page starts our server with that champion and nine bots (picked by position) and
rem then the game; closing the game brings the page back to the lobby.
rem Vanguard must not be running (exit it from its tray icon): the game copy is only started without it.
rem Close this window to stop the page's server. The match's server log: data\exe1620\play_server.log
set P=%~dp0
set BA_PATCH=1620
start "" http://127.0.0.1:5180/
python "%P%launcher\lobby_server.py" 5180
