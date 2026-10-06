# lobby.exe: the out-of-game client (League's LCU: a local HTTP service + a web page). It starts server.exe and client.exe.
add_executable(ba_lobby src/main.cpp)
target_link_libraries(ba_lobby PRIVATE ba_common ws2_32 shell32 advapi32)
set_target_properties(ba_lobby PROPERTIES OUTPUT_NAME lobby)
# the page, next to the exe
add_custom_target(ba_lobby_assets
  COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_CURRENT_SOURCE_DIR}/www $<TARGET_FILE_DIR:ba_lobby>/lobby_www)
add_dependencies(ba_lobby ba_lobby_assets)
