# client.exe: draws the match with DirectX 11 (feature level 11_0, League's minimum) and sends the player's orders.
add_executable(ba_client WIN32
  src/main.cpp
  src/Gpu.cpp
  src/MapView.cpp
  src/Character.cpp
  src/Vfx.cpp
  src/Connection.cpp
  src/Replay.cpp
  src/RiotShader.cpp
  src/Hud.cpp
  src/Ui.cpp
  src/LoadingScreen.cpp
)
target_link_libraries(ba_client PRIVATE ba_common enet d3d11 dxgi d3dcompiler dxguid gdi32)
if(NOT MSVC)
  target_link_options(ba_client PRIVATE -municode)  # wWinMain
endif()
set_target_properties(ba_client PROPERTIES OUTPUT_NAME client)
