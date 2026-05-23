cmake_minimum_required(VERSION 3.16)
project(pe_native CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# SDL2
find_package(SDL2 REQUIRED)

# Compiler flags
if(MSVC)
    add_compile_options(/W4 /permissive-)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Intro viewer (Phase A → C++)
add_executable(pe_intro_viewer
    src/main.cpp
    src/CcArchive.cpp
    src/Lzw.cpp
    src/VgaRenderer.cpp
)
target_include_directories(pe_intro_viewer PRIVATE src ${SDL2_INCLUDE_DIRS})
target_link_libraries(pe_intro_viewer PRIVATE ${SDL2_LIBRARIES})
