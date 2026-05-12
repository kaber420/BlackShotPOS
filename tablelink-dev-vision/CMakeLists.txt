# Blackshot IoT - Build Configuration
# Copyright (C) 2026 Fco Ivan Romero Guzman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

cmake_minimum_required(VERSION 3.10)
project(BlackshotUISDK)

set(CMAKE_CXX_STANDARD 17)

# --- Dependencias del Sistema ---
find_package(Threads REQUIRED)
find_package(SDL2 REQUIRED)
find_package(ZLIB REQUIRED)

include(FetchContent)

# --- Dependencias Externas (Descarga rápida mediante URL) ---

# 1. IXWebSocket
FetchContent_Declare(
  ixwebsocket
  URL https://github.com/machinezone/IXWebSocket/archive/refs/tags/v11.4.4.tar.gz
)
FetchContent_MakeAvailable(ixwebsocket)

# 2. JSON (ArduinoJson - Optimized for Embedded/IoT)
FetchContent_Declare(
  ArduinoJson
  URL https://github.com/bblanchon/ArduinoJson/archive/refs/tags/v7.0.4.tar.gz
)
FetchContent_MakeAvailable(ArduinoJson)

# 3. LVGL (Simulación x86)
FetchContent_Declare(
  lvgl
  URL https://github.com/lvgl/lvgl/archive/refs/tags/v9.1.0.tar.gz
  # Parche automático: Eliminar archivos de ensamblador ARM para evitar errores en x86
  PATCH_COMMAND find . -name "*.S" -delete
)
FetchContent_MakeAvailable(lvgl)

# --- Configuración de Layout ---
option(BS_LAYOUT_MODERN "Habilita la interfaz moderna estilo Dashboard (Recomendado 4.3\"+)" OFF)

if(BS_LAYOUT_MODERN)
    set(SCREEN_WIDTH 480)
    set(SCREEN_HEIGHT 272)
    add_definitions(-DBS_LAYOUT_MODERN)
else()
    set(SCREEN_WIDTH 320)
    set(SCREEN_HEIGHT 240)
endif()

# --- Selección de Tema ---
set(BS_THEME "DARK" CACHE STRING "Selecciona el tema: DARK, CYBERPUNK, MIDNIGHT, MINIMAL, LIGHT, DASHBOARD_BLUE")
if(BS_THEME STREQUAL "DARK")
    add_definitions(-DBS_THEME_DARK)
elseif(BS_THEME STREQUAL "CYBERPUNK")
    add_definitions(-DBS_THEME_CYBERPUNK)
elseif(BS_THEME STREQUAL "MIDNIGHT")
    add_definitions(-DBS_THEME_MIDNIGHT)
elseif(BS_THEME STREQUAL "MINIMAL")
    add_definitions(-DBS_THEME_MINIMAL)
elseif(BS_THEME STREQUAL "LIGHT")
    add_definitions(-DBS_THEME_LIGHT)
elseif(BS_THEME STREQUAL "DASHBOARD_BLUE")
    add_definitions(-DBS_THEME_DASHBOARD_BLUE)
endif()

# Forzar soporte SDL en el build de LVGL
set(LV_USE_SDL ON CACHE BOOL "Enable SDL support")
set(LV_CONF_PATH ${CMAKE_CURRENT_SOURCE_DIR}/lv_conf.h CACHE FILEPATH "Path to LVGL config")

# Configuración de LVGL para usar cabeceras simples
set(LV_CONF_BUILD_DISABLE ON) 
add_definitions(-DLV_CONF_INCLUDE_SIMPLE)
add_definitions(-DLV_LVGL_H_INCLUDE_SIMPLE)

# Rutas de Inclusión
include_directories(${CMAKE_CURRENT_SOURCE_DIR})
include_directories(${lvgl_SOURCE_DIR})

# Asegurar que el subproyecto LVGL encuentre nuestro lv_conf.h
target_include_directories(lvgl PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# --- Ejecutable y Enlazado ---

# Archivos de Fuente
file(GLOB_RECURSE SOURCES "src/*.cpp" "src/*.h")

add_executable(${PROJECT_NAME} ${SOURCES})

# Incluir directorios de SDL2 explícitamente para el compilador
target_include_directories(${PROJECT_NAME} PRIVATE ${SDL2_INCLUDE_DIRS})

target_link_libraries(${PROJECT_NAME} 
    lvgl 
    lvgl::thorvg 
    ${SDL2_LIBRARIES} 
    ixwebsocket::ixwebsocket 
    ArduinoJson
    Threads::Threads
)

add_definitions(-DSCREEN_WIDTH=${SCREEN_WIDTH})
add_definitions(-DSCREEN_HEIGHT=${SCREEN_HEIGHT})

message(STATUS "Blackshot UI SDK Configurado - Layout: ${BS_LAYOUT_MODERN}, Tema: ${BS_THEME}, Resolución: ${SCREEN_WIDTH}x${SCREEN_HEIGHT}")
