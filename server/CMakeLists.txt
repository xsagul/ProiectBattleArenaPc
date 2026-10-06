# server.exe: one match, simulated on a single thread at League's 30.3 ticks per second.
add_executable(ba_server
  src/main.cpp
  src/Match.cpp
  src/MatchSpells.cpp
  src/MatchLevel.cpp
  src/MatchAI.cpp
  src/Recorder.cpp
)
target_link_libraries(ba_server PRIVATE ba_common enet lua51)
set_target_properties(ba_server PROPERTIES OUTPUT_NAME server)
# the spells' scripts, next to the exe
add_custom_command(TARGET ba_server POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_CURRENT_SOURCE_DIR}/scripts $<TARGET_FILE_DIR:ba_server>/scripts)
