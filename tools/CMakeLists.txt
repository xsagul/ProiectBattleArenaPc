# bainfo: looks inside League's files with the same parsers the game uses (lists WADs, dumps .bin entries), to check
# them against the Python tools of BattleArena.
add_executable(bainfo bainfo.cpp)
target_link_libraries(bainfo PRIVATE ba_common lua51)
add_executable(animation_audit animation_audit.cpp)
target_link_libraries(animation_audit PRIVATE ba_common)
if(WIN32)
  target_link_libraries(bainfo PRIVATE d3dcompiler)
endif()
