cmake_minimum_required(VERSION 3.20)
project(cold_trail LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
FetchContent_Declare(json
  URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
FetchContent_MakeAvailable(json)

file(GLOB CORE_SOURCES CONFIGURE_DEPENDS src/*.cpp)
list(FILTER CORE_SOURCES EXCLUDE REGEX "src/main\\.cpp$")
add_library(detective_core STATIC ${CORE_SOURCES})
target_include_directories(detective_core PUBLIC src)
target_link_libraries(detective_core PUBLIC nlohmann_json::nlohmann_json)
target_compile_definitions(detective_core PUBLIC COLD_TRAIL_DATA_DIR="${CMAKE_SOURCE_DIR}/data")

add_executable(detective src/main.cpp)
target_link_libraries(detective PRIVATE detective_core)

if(MINGW)
  # Start without the toolchain on PATH: embed libgcc/libstdc++, ship winpthread beside the exe.
  target_link_options(detective PRIVATE -static-libgcc -static-libstdc++)
  get_filename_component(MINGW_BIN_DIR "${CMAKE_CXX_COMPILER}" DIRECTORY)
  find_file(WINPTHREAD_DLL libwinpthread-1.dll HINTS "${MINGW_BIN_DIR}" REQUIRED)
  add_custom_command(TARGET detective POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${WINPTHREAD_DLL}" "$<TARGET_FILE_DIR:detective>")
endif()

enable_testing()
FetchContent_Declare(googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)
add_subdirectory(tests)
