#ifndef BLACKSHOT_THEMES_H
#define BLACKSHOT_THEMES_H

#include "lvgl.h"

/**
 * @file themes.h
 * @brief Definición del sistema de temas de Blackshot.
 */

// --- SELECCIÓN DE TEMA ---
#if !defined(BS_THEME_DARK) && !defined(BS_THEME_CYBERPUNK) && !defined(BS_THEME_MIDNIGHT) && \
    !defined(BS_THEME_MINIMAL) && !defined(BS_THEME_LIGHT) && !defined(BS_THEME_DASHBOARD_BLUE)
    #define BS_THEME_DARK
#endif

// ==========================================
// TEMA: DARK NEON (Default)
// ==========================================
#ifdef BS_THEME_DARK
    #define BS_COLOR_BG          lv_color_hex(0x0A0A0A)
    #define BS_COLOR_PRIMARY     lv_color_hex(0x00FF88) // Verde neón
    #define BS_COLOR_SECONDARY   lv_color_hex(0x00D4FF) // Azul
    #define BS_COLOR_ACCENT      lv_color_hex(0xFF00FF) // Fuchsia
    #define BS_COLOR_CARD        lv_color_hex(0x181818)
    #define BS_COLOR_CARD_BORDER lv_color_hex(0x2A2A2A)
    #define BS_COLOR_TEXT        lv_color_hex(0xFFFFFF)
    #define BS_COLOR_TEXT_DIM    lv_color_hex(0x888888)
#endif

// ==========================================
// TEMA: LIGHT (Clean & Professional)
// ==========================================
#ifdef BS_THEME_LIGHT
    #define BS_COLOR_BG          lv_color_hex(0xF5F5F7) // iOS Light Gray
    #define BS_COLOR_PRIMARY     lv_color_hex(0x007AFF) // Azure Blue
    #define BS_COLOR_SECONDARY   lv_color_hex(0x5856D6) // Indigo
    #define BS_COLOR_ACCENT      lv_color_hex(0xFF2D55) // Pink
    #define BS_COLOR_CARD        lv_color_hex(0xFFFFFF) // Pure White
    #define BS_COLOR_CARD_BORDER lv_color_hex(0xCECED2) // Soft Border
    #define BS_COLOR_TEXT        lv_color_hex(0x1C1C1E) // Near Black
    #define BS_COLOR_TEXT_DIM    lv_color_hex(0x8E8E93) // Gray
#endif

// ==========================================
// TEMA: CYBERPUNK (High Contrast)
// ==========================================
#ifdef BS_THEME_CYBERPUNK
    #define BS_COLOR_BG          lv_color_hex(0x00050D)
    #define BS_COLOR_PRIMARY     lv_color_hex(0xFFFF00) // Amarillo Neón
    #define BS_COLOR_SECONDARY   lv_color_hex(0x00FFFF) // Cyan
    #define BS_COLOR_ACCENT      lv_color_hex(0xFF0055) // Cyber Red
    #define BS_COLOR_CARD        lv_color_hex(0x0A0F1E)
    #define BS_COLOR_CARD_BORDER lv_color_hex(0x203050)
    #define BS_COLOR_TEXT        lv_color_hex(0xFFFFFF)
    #define BS_COLOR_TEXT_DIM    lv_color_hex(0x00D4FF)
#endif

// ==========================================
// TEMA: MIDNIGHT (Deep Indigo)
// ==========================================
#ifdef BS_THEME_MIDNIGHT
    #define BS_COLOR_BG          lv_color_hex(0x020205)
    #define BS_COLOR_PRIMARY     lv_color_hex(0xA080FF) // Lavanda neón
    #define BS_COLOR_SECONDARY   lv_color_hex(0x4060FF) // Azul profundo
    #define BS_COLOR_ACCENT      lv_color_hex(0xFF80C0) // Rosa pastel
    #define BS_COLOR_CARD        lv_color_hex(0x0C0C14)
    #define BS_COLOR_CARD_BORDER lv_color_hex(0x1A1A2E)
    #define BS_COLOR_TEXT        lv_color_hex(0xE0E0FF)
    #define BS_COLOR_TEXT_DIM    lv_color_hex(0x606080)
#endif

// ==========================================
// TEMA: DASHBOARD BLUE (Modern & Professional)
// ==========================================
#ifdef BS_THEME_DASHBOARD_BLUE
    #define BS_COLOR_BG          lv_color_hex(0x020815) // Ultra Deep Navy
    #define BS_COLOR_PRIMARY     lv_color_hex(0x00F2FF) // Higher Vibrance Cyan
    #define BS_COLOR_SECONDARY   lv_color_hex(0x3B82F6) // Modern Blue
    #define BS_COLOR_ACCENT      lv_color_hex(0xFB923C) // Warm Orange
    #define BS_COLOR_CARD        lv_color_hex(0x0F172A) // Lighter Navy for contrast
    #define BS_COLOR_CARD_BORDER lv_color_hex(0x1E293B) 
    #define BS_COLOR_TEXT        lv_color_hex(0xF8FAFC)
    #define BS_COLOR_TEXT_DIM    lv_color_hex(0x94A3B8)
#endif

// ==========================================
// COLORES DE ESTADO
// ==========================================
#define BS_COLOR_ERROR       lv_color_hex(0xFF4444)
#define BS_COLOR_QUEUE       lv_color_hex(0xFFCC00)
#define BS_COLOR_PREPARING   lv_color_hex(0x00AAFF)
#define BS_COLOR_READY       lv_color_hex(0x00FF88)
#define BS_COLOR_DELIVERED   lv_color_hex(0xFF44AA)

// Colores de Advertencia / Modificaciones
#define BS_COLOR_WARNING     lv_color_hex(0xFF9500) // Naranja iOS

// Configuraciones Visuales High-Fidelity
#define BS_RADIUS_DEFAULT    20
#define BS_RADIUS_CARD       20
#define BS_BORDER_WIDTH      1
#define BS_OPACITY_GLASS     190 
#define BS_ANIM_DURATION     500 // Más elegante
#define BS_SHADOW_OPA        40
#define BS_GLOW_OPA_MIN      40
#define BS_GLOW_OPA_MAX      180

#endif // BLACKSHOT_THEMES_H
