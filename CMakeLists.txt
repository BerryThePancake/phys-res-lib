cmake_minimum_required(VERSION 3.16)
project(physresidual C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(physresidual SHARED src/physresidual.c)
target_include_directories(physresidual PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_definitions(physresidual PRIVATE PHYSRESIDUAL_BUILD)
if(MSVC)
    target_compile_definitions(physresidual PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()

add_library(physresidual_static STATIC src/physresidual.c)
target_include_directories(physresidual_static PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_definitions(physresidual_static PUBLIC PHYSRESIDUAL_STATIC)
set_target_properties(physresidual_static PROPERTIES OUTPUT_NAME physresidual POSITION_INDEPENDENT_CODE ON)

add_executable(example_power examples/example_power.c)
target_link_libraries(example_power PRIVATE physresidual_static)

# Portable single-file CLI (statically link library objects; no separate DLL at runtime).
add_executable(physresidual_cli tools/physresidual_cli.c)
target_link_libraries(physresidual_cli PRIVATE physresidual_static)
if(MSVC)
    set_property(TARGET physresidual_cli PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()
if(MINGW)
    target_link_options(physresidual_cli PRIVATE -static)
endif()
