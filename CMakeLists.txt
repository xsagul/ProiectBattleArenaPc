# BattleArena PC: a League-style native client (C++ / DirectX 11) and match server (C++), built with MSVC + CMake.
#
#   cmake -S . -B build -G "Visual Studio 17 2022" -A x64
#   cmake --build build --config Release
#
# Third-party sources (ENet, Lua 5.1, zstd, xxHash) live in third_party/ (cmake/Dependencies.cmake).

cmake_minimum_required(VERSION 3.24)
project(BattleArenaPc LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

add_compile_definitions(_CRT_SECURE_NO_WARNINGS NOMINMAX WIN32_LEAN_AND_MEAN UNICODE _UNICODE)
if(MSVC)
  add_compile_options(/W4 /permissive- /utf-8 /MP)
else()
  # Clang (llvm-mingw) until Visual Studio is installed: same C++20 and DirectX 11 code, another compiler.
  add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wall> $<$<COMPILE_LANGUAGE:CXX>:-Wextra>)
  add_link_options(-static)
endif()

include(cmake/Dependencies.cmake)

add_subdirectory(common)
add_subdirectory(server)
add_subdirectory(client)
add_subdirectory(lobby)
add_subdirectory(tools)
