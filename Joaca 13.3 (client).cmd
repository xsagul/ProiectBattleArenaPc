@echo off
rem The out-of-game client on League Client 13.3's files (lobby\www13) served by launcher\lobby_server.py, opened in
rem the browser. PLAY -> Summoner's Rift -> Confirm -> Find Match -> Accept -> pick a champion -> Lock In: the page
rem starts our game server and the 13.3 game with that champion; closing the game brings the page back to the lobby.
rem Close this window to stop the page's server.
set P=%~dp0
start "" http://127.0.0.1:5180/
python "%P%launcher\lobby_server.py" 5180
