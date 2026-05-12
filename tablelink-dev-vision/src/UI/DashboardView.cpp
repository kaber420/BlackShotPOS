#include "DashboardView.h"
#include "../State/AppState.h"
#include "../State/EventBus.h"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <ctime>

namespace UI {

lv_obj_t* DashboardView::screen = nullptr;
lv_obj_t* DashboardView::header = nullptr;
lv_obj_t* DashboardView::clock_label = nullptr;
lv_obj_t* DashboardView::business_label = nullptr;
lv_obj_t* DashboardView::table_id_label = nullptr;
lv_obj_t* DashboardView::order_id_label = nullptr;
lv_obj_t* DashboardView::tablepad_cont = nullptr;
lv_obj_t* DashboardView::footer = nullptr;
lv_obj_t* DashboardView::sidebar = nullptr;
lv_obj_t* DashboardView::main_content = nullptr;
lv_obj_t* DashboardView::status_led = nullptr;
lv_obj_t* DashboardView::offline_cont = nullptr;
lv_obj_t* DashboardView::goodbye_overlay = nullptr;

std::map<int, DishCardWidgets> DashboardView::active_dish_cards;
bool DashboardView::bill_requested = false;

lv_style_t DashboardView::style_card;
lv_style_t DashboardView::style_btn;
lv_style_t DashboardView::style_text_small;
lv_style_t DashboardView::style_badge;
lv_style_t DashboardView::style_btn_icon;
lv_style_t DashboardView::style_item_badge;
lv_style_t DashboardView::style_mod_badge;

// ─── Helpers ──────────────────────────────────────────
static lv_color_t status_to_color(const std::string& s) {
    if (s == "PREPARANDO") return BS_COLOR_PREPARING;
    if (s == "LISTO")      return BS_COLOR_READY;
    if (s == "ENTREGADO")  return BS_COLOR_DELIVERED;
    return BS_COLOR_QUEUE;
}

static const char* status_to_short(const std::string& s) {
    if (s == "PREPARANDO") return "PREP";
    if (s == "LISTO")      return "LISTO";
    if (s == "ENTREGADO")  return "ENTG";
    return "COLA";
}

static void anim_y_cb(void* var, int32_t v)   { lv_obj_set_y((lv_obj_t*)var, v); }
static void anim_opa_cb(void* var, int32_t v)  { lv_obj_set_style_opa((lv_obj_t*)var, (uint8_t)v, 0); }

static void update_clock_timer_cb(lv_timer_t* t) {
    lv_obj_t* label = (lv_obj_t*)t->user_data;
    std::time_t now = std::time(nullptr);
    std::tm* ltm = std::localtime(&now);
    char buf[16];
    std::strftime(buf, sizeof(buf), "%H:%M:%S", ltm);
    lv_label_set_text(label, buf);
}

// ─── init_styles ──────────────────────────────────────
void DashboardView::init_styles() {
    // Card Principal (High-Fidelity Floating)
    lv_style_init(&style_card);
    lv_style_set_bg_color(&style_card, BS_COLOR_CARD);
    lv_style_set_bg_opa(&style_card, BS_OPACITY_GLASS);
    lv_style_set_radius(&style_card, BS_RADIUS_CARD);
    
    // Gradiente sutil
    lv_style_set_bg_grad_color(&style_card, lv_color_darken(BS_COLOR_CARD, 8));
    lv_style_set_bg_grad_dir(&style_card, LV_GRAD_DIR_VER);

    // Sombreado realista (Efecto profundidad)
    lv_style_set_shadow_width(&style_card, 25);
    lv_style_set_shadow_spread(&style_card, 2);
    lv_style_set_shadow_color(&style_card, lv_color_hex(0x000000));
    lv_style_set_shadow_opa(&style_card, BS_SHADOW_OPA);
    lv_style_set_shadow_ofs_y(&style_card, 4);

    // Rim Lighting (Highlight interno superior)
    lv_style_set_outline_width(&style_card, 1);
    lv_style_set_outline_color(&style_card, lv_color_lighten(BS_COLOR_CARD, 20));
    lv_style_set_outline_opa(&style_card, 90);
    lv_style_set_outline_pad(&style_card, -1); // Outline metido hacia adentro

    // Badges Genéricos
    lv_style_init(&style_badge);
    lv_style_set_bg_color(&style_badge, BS_COLOR_BG);
    lv_style_set_bg_opa(&style_badge, 120);
    lv_style_set_border_width(&style_badge, 1);
    lv_style_set_border_color(&style_badge, BS_COLOR_CARD_BORDER);
    lv_style_set_radius(&style_badge, 8);
    lv_style_set_text_color(&style_badge, BS_COLOR_TEXT_DIM);
    lv_style_set_text_font(&style_badge, &lv_font_montserrat_12);

    // Badge de Modificación (High-end Warning)
    lv_style_init(&style_mod_badge);
    lv_style_set_bg_color(&style_mod_badge, BS_COLOR_WARNING);
    lv_style_set_bg_opa(&style_mod_badge, 35);
    lv_style_set_border_color(&style_mod_badge, BS_COLOR_WARNING);
    lv_style_set_border_width(&style_mod_badge, 1);
    lv_style_set_radius(&style_mod_badge, 10);
    lv_style_set_text_color(&style_mod_badge, BS_COLOR_WARNING);
    lv_style_set_text_font(&style_mod_badge, &lv_font_montserrat_12);

    // Botones Nav
    lv_style_init(&style_btn_icon);
    lv_style_set_bg_color(&style_btn_icon, lv_color_lighten(BS_COLOR_BG, 5));
    lv_style_set_radius(&style_btn_icon, 16);
    lv_style_set_border_width(&style_btn_icon, 1);
    lv_style_set_border_color(&style_btn_icon, BS_COLOR_CARD_BORDER);
    lv_style_set_shadow_width(&style_btn_icon, 8);
    lv_style_set_shadow_opa(&style_btn_icon, 40);
}

// ─── setup_screen ─────────────────────────────────────
void DashboardView::setup_screen(lv_obj_t* parent) {
    screen = parent;
    lv_obj_set_style_bg_color(screen, BS_COLOR_BG, 0);

    #ifdef BS_LAYOUT_MODERN
        setup_modern_dashboard(screen);
    #else
        setup_classic_list(screen);
    #endif
}

// ─── setup_classic_list ───────────────────────────────
void DashboardView::setup_classic_list(lv_obj_t* parent) {

    // Header
    header = lv_obj_create(screen);
    lv_obj_set_size(header, lv_pct(100), 48);
    lv_obj_align(header, LV_ALIGN_TOP_MID, 0, 0);
    lv_obj_set_style_bg_color(header, BS_COLOR_BG, 0);
    lv_obj_set_style_bg_grad_color(header, BS_COLOR_CARD, 0);
    lv_obj_set_style_bg_grad_dir(header, LV_GRAD_DIR_VER, 0);
    lv_obj_set_style_border_side(header, LV_BORDER_SIDE_BOTTOM, 0);
    lv_obj_set_style_border_color(header, BS_COLOR_CARD_BORDER, 0);
    lv_obj_set_style_border_width(header, 1, 0);
    lv_obj_set_style_radius(header, 0, 0);
    lv_obj_set_style_pad_hor(header, 12, 0);

    business_label = lv_label_create(header);
    lv_label_set_text(business_label, State::AppState::get_business_name().c_str());
    lv_obj_set_style_text_font(business_label, &lv_font_montserrat_14, 0);
    lv_obj_align(business_label, LV_ALIGN_CENTER, 0, 0);

    clock_label = lv_label_create(header);
    lv_obj_set_style_text_font(clock_label, &lv_font_montserrat_12, 0);
    lv_obj_set_style_text_color(clock_label, BS_COLOR_TEXT_DIM, 0);
    lv_obj_align(clock_label, LV_ALIGN_RIGHT_MID, 0, 0);
    lv_timer_create(update_clock_timer_cb, 1000, clock_label);

    // Footer
    footer = lv_obj_create(screen);
    lv_obj_set_size(footer, lv_pct(100), 55);
    lv_obj_align(footer, LV_ALIGN_BOTTOM_MID, 0, 0);
    lv_obj_set_style_bg_color(footer, BS_COLOR_BG, 0);
    lv_obj_set_style_radius(footer, 0, 0);
    lv_obj_set_style_border_side(footer, LV_BORDER_SIDE_TOP, 0);
    lv_obj_set_style_border_color(footer, BS_COLOR_CARD_BORDER, 0);
    lv_obj_set_style_border_width(footer, 1, 0);
    lv_obj_set_flex_flow(footer, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(footer, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_gap(footer, 10, 0);

    const char* labels[]  = {"MESERO", "CUENTA", "MAS"};
    const char* syms[]    = {LV_SYMBOL_BELL, LV_SYMBOL_CHARGE, LV_SYMBOL_LIST};
    const char* actions[] = {"call_waiter", "request_bill", "open_menu"};

    for(int i=0; i<3; i++) {
        lv_obj_t* b = lv_obj_create(footer);
        lv_obj_set_size(b, 90, 40);
        lv_obj_add_style(b, &style_btn_icon, 0);
        lv_obj_add_flag(b, LV_OBJ_FLAG_CLICKABLE);
        lv_obj_clear_flag(b, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_flex_flow(b, LV_FLEX_FLOW_COLUMN);
        lv_obj_set_flex_align(b, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
        lv_obj_set_style_pad_all(b, 2, 0);
        lv_obj_set_style_pad_gap(b, 0, 0);

        // Micro-interacción: Escala al pulsar
        lv_obj_add_event_cb(b, [](lv_event_t* e) {
            lv_obj_t* btn = lv_event_get_current_target_obj(e);
            if (lv_event_get_code(e) == LV_EVENT_PRESSED) {
                lv_obj_set_style_transform_scale(btn, 240, 0); // Un poco más pequeño
            } else if (lv_event_get_code(e) == LV_EVENT_RELEASED || lv_event_get_code(e) == LV_EVENT_PRESS_LOST) {
                lv_obj_set_style_transform_scale(btn, 256, 0); // Escala normal (256 = 1.0)
            }
        }, LV_EVENT_ALL, nullptr);
        
        lv_obj_t* s = lv_label_create(b); lv_label_set_text(s, syms[i]);
        lv_obj_set_style_text_color(s, BS_COLOR_PRIMARY, 0);
        lv_obj_t* l = lv_label_create(b); lv_label_set_text(l, labels[i]);
        lv_obj_set_style_text_font(l, &lv_font_montserrat_12, 0);

        if (i != 1) { // MESERO y MAS
            struct ActionData { std::string act; };
            ActionData* data = new ActionData{actions[i]};
            lv_obj_add_event_cb(b, [](lv_event_t* e) {
                ActionData* d = (ActionData*)lv_event_get_user_data(e);
                State::EventBus::push_ui_action({d->act, ""});
                lv_obj_t* btn = lv_event_get_current_target_obj(e);
                lv_obj_set_style_bg_color(btn, BS_COLOR_PRIMARY, 0);
                lv_obj_set_style_text_color(lv_obj_get_child(btn, 0), BS_COLOR_BG, 0);
                lv_obj_set_style_text_color(lv_obj_get_child(btn, 1), BS_COLOR_BG, 0);
            }, LV_EVENT_CLICKED, data);
        } else { // CUENTA (2 Fases)
            lv_obj_add_event_cb(b, [](lv_event_t* e) {
                lv_obj_t* btn = lv_event_get_current_target_obj(e);
                lv_obj_t* s_lbl = lv_obj_get_child(btn, 0);
                lv_obj_t* t_lbl = lv_obj_get_child(btn, 1);

                if (!DashboardView::bill_requested) {
                    State::EventBus::push_ui_action({"request_bill", ""});
                    DashboardView::bill_requested = true;
                    lv_label_set_text(s_lbl, LV_SYMBOL_OK);
                    lv_label_set_text(t_lbl, "LIBERAR");
                    lv_obj_set_style_bg_color(btn, lv_color_hex(0x081A0D), 0);
                    lv_obj_set_style_border_color(btn, BS_COLOR_PRIMARY, 0);
                } else {
                    State::EventBus::push_ui_action({"clear_table", ""});
                    DashboardView::bill_requested = false;
                    DashboardView::show_goodbye_screen();
                    lv_label_set_text(s_lbl, LV_SYMBOL_CHARGE);
                    lv_label_set_text(t_lbl, "CUENTA");
                    lv_obj_set_style_bg_color(btn, lv_color_hex(0x181818), 0);
                    lv_obj_set_style_border_color(btn, BS_COLOR_CARD_BORDER, 0);
                }
            }, LV_EVENT_CLICKED, nullptr);
        }
    }

    // Contenedor principal
    tablepad_cont = lv_obj_create(screen);
    lv_obj_set_size(tablepad_cont, lv_pct(100), 137);
    lv_obj_align(tablepad_cont, LV_ALIGN_TOP_MID, 0, 48);
    lv_obj_set_style_bg_opa(tablepad_cont, 0, 0);
    lv_obj_set_style_border_width(tablepad_cont, 0, 0);
    lv_obj_set_flex_flow(tablepad_cont, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_style_pad_all(tablepad_cont, 10, 0);
    lv_obj_set_style_pad_gap(tablepad_cont, 12, 0);
    lv_obj_set_scrollbar_mode(tablepad_cont, LV_SCROLLBAR_MODE_AUTO);
}

// ─── setup_modern_dashboard ───────────────────────────
void DashboardView::setup_modern_dashboard(lv_obj_t* parent) {
    // 1. Sidebar (Control Pad - 60px)
    sidebar = lv_obj_create(parent);
    lv_obj_set_size(sidebar, 64, lv_pct(100));
    lv_obj_align(sidebar, LV_ALIGN_LEFT_MID, 0, 0);
    lv_obj_set_style_bg_color(sidebar, BS_COLOR_CARD, 0);
    lv_obj_set_style_border_side(sidebar, LV_BORDER_SIDE_RIGHT, 0);
    lv_obj_set_style_border_color(sidebar, BS_COLOR_CARD_BORDER, 0);
    lv_obj_set_style_border_width(sidebar, 1, 0);
    lv_obj_set_style_radius(sidebar, 0, 0);
    lv_obj_set_flex_flow(sidebar, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_flex_align(sidebar, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_all(sidebar, 8, 0);
    lv_obj_set_style_pad_gap(sidebar, 15, 0);

    // Sidebar Icons (Simulando navegación + Botonera interactiva)
    const char* side_syms[] = {LV_SYMBOL_HOME, LV_SYMBOL_BELL, LV_SYMBOL_CHARGE, LV_SYMBOL_PLUS};
    const char* side_acts[] = {"home", "call_waiter", "request_bill", "open_menu"};
    
    for(int i=0; i<4; i++) {
        lv_obj_t* btn = lv_obj_create(sidebar);
        lv_obj_set_size(btn, 48, 48);
        lv_obj_add_style(btn, &style_btn_icon, 0);
        lv_obj_set_style_radius(btn, 12, 0);
        lv_obj_clear_flag(btn, LV_OBJ_FLAG_SCROLLABLE);
        
        lv_obj_t* icon = lv_label_create(btn);
        lv_label_set_text(icon, side_syms[i]);
        lv_obj_set_style_text_font(icon, &lv_font_montserrat_18, 0);
        lv_obj_set_style_text_color(icon, (i == 0) ? BS_COLOR_PRIMARY : BS_COLOR_TEXT_DIM, 0);
        lv_obj_center(icon);

        // Lógica de acción
        if (i == 2) { // CUENTA (Botonera especial 2 fases)
            lv_obj_add_event_cb(btn, [](lv_event_t* e) {
                lv_obj_t* b = lv_event_get_current_target_obj(e);
                lv_obj_t* ic = lv_obj_get_child(b, 0);
                if (!DashboardView::bill_requested) {
                    State::EventBus::push_ui_action({"request_bill", ""});
                    DashboardView::bill_requested = true;
                    lv_label_set_text(ic, LV_SYMBOL_OK);
                    lv_obj_set_style_bg_color(b, lv_color_hex(0x081A0D), 0);
                    lv_obj_set_style_border_color(b, BS_COLOR_PRIMARY, 0);
                } else {
                    State::EventBus::push_ui_action({"clear_table", ""});
                    DashboardView::bill_requested = false;
                    DashboardView::show_goodbye_screen();
                    lv_label_set_text(ic, LV_SYMBOL_CHARGE);
                    lv_obj_set_style_bg_color(b, lv_color_hex(0x181818), 0);
                    lv_obj_set_style_border_color(b, BS_COLOR_CARD_BORDER, 0);
                }
            }, LV_EVENT_CLICKED, nullptr);
        } else {
            std::string* act_data = new std::string(side_acts[i]);
            lv_obj_add_event_cb(btn, [](lv_event_t* e) {
                std::string* act = (std::string*)lv_event_get_user_data(e);
                State::EventBus::push_ui_action({*act, ""});
                lv_obj_t* b = lv_event_get_current_target_obj(e);
                lv_obj_set_style_bg_color(b, BS_COLOR_PRIMARY, 0);
                lv_obj_set_style_text_color(lv_obj_get_child(b, 0), BS_COLOR_BG, 0);
            }, LV_EVENT_CLICKED, (void*)act_data);
        }
    }

    // 2. Main Content Area
    main_content = lv_obj_create(parent);
    lv_obj_set_size(main_content, lv_pct(100), lv_pct(100));
    lv_obj_set_x(main_content, 64);
    // FIX: El ancho debe ser el 100% MENOS el sidebar para evitar el overflow
    lv_obj_set_width(main_content, lv_pct(100)); // Mantener para el cálculo, pero usar el x offset correctamente
    lv_obj_update_layout(parent);
    lv_obj_set_width(main_content, lv_obj_get_width(parent) - 64);
    lv_obj_set_style_bg_opa(main_content, 0, 0);
    lv_obj_set_style_border_width(main_content, 0, 0);
    lv_obj_set_style_pad_all(main_content, 15, 0);
    lv_obj_clear_flag(main_content, LV_OBJ_FLAG_SCROLLABLE);

    // Modern Header (Dins del Area Principal)
    header = lv_obj_create(main_content);
    lv_obj_set_size(header, lv_pct(100), 50);
    lv_obj_align(header, LV_ALIGN_TOP_MID, 0, 0);
    lv_obj_set_style_bg_opa(header, 0, 0);
    lv_obj_set_style_border_side(header, LV_BORDER_SIDE_BOTTOM, 0);
    lv_obj_set_style_border_color(header, BS_COLOR_CARD_BORDER, 0);
    lv_obj_set_style_border_width(header, 1, 0);
    lv_obj_set_style_radius(header, 0, 0);
    lv_obj_set_style_pad_hor(header, 5, 0);

    business_label = lv_label_create(header);
    lv_label_set_text(business_label, State::AppState::get_business_name().c_str());
    lv_obj_set_style_text_font(business_label, &lv_font_montserrat_18, 0);
    lv_obj_align(business_label, LV_ALIGN_LEFT_MID, 0, 0);

    // Mesa Info (Junto al nombre)
    table_id_label = lv_label_create(header);
    lv_label_set_text(table_id_label, ""); // Se llena en add_order
    lv_obj_set_style_text_font(table_id_label, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(table_id_label, BS_COLOR_TEXT_DIM, 0);
    lv_obj_align(table_id_label, LV_ALIGN_LEFT_MID, 180, 0); // Ajuste manual de offset

    // Order ID (Badge-style en el header)
    order_id_label = lv_label_create(header);
    lv_label_set_text(order_id_label, ""); 
    lv_obj_set_style_text_font(order_id_label, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(order_id_label, BS_COLOR_PRIMARY, 0);
    lv_obj_align(order_id_label, LV_ALIGN_LEFT_MID, 260, 0);

    clock_label = lv_label_create(header);
    lv_obj_set_style_text_font(clock_label, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(clock_label, BS_COLOR_TEXT_DIM, 0);
    lv_obj_align(clock_label, LV_ALIGN_RIGHT_MID, 0, 0);
    lv_timer_create(update_clock_timer_cb, 1000, clock_label);

    // 3. Grid Dynamics (Atomic Cards container)
    tablepad_cont = lv_obj_create(main_content);
    lv_obj_set_size(tablepad_cont, lv_pct(100), lv_pct(80));
    lv_obj_align(tablepad_cont, LV_ALIGN_TOP_MID, 0, 60);
    lv_obj_set_style_bg_opa(tablepad_cont, 0, 0);
    lv_obj_set_style_border_width(tablepad_cont, 0, 0);
    
    // AQUÍ ESTÁ EL CAMBIO CLAVE: Modo GRID para Modern Layout
    lv_obj_set_flex_flow(tablepad_cont, LV_FLEX_FLOW_ROW_WRAP);
    lv_obj_set_flex_align(tablepad_cont, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_START);
    
    lv_obj_set_style_pad_all(tablepad_cont, 0, 0);
    lv_obj_set_style_pad_gap(tablepad_cont, 15, 0);
    lv_obj_set_scrollbar_mode(tablepad_cont, LV_SCROLLBAR_MODE_AUTO);
}

// ─── create_dish_card ─────────────────────────────────
lv_obj_t* DashboardView::create_dish_card(lv_obj_t* parent, const DishItem& dish, int order_id, const char* table_name) {
    lv_obj_t* card = lv_obj_create(parent);
    
    #ifdef BS_LAYOUT_MODERN
        lv_obj_set_size(card, 195, 135); // Tamaño "Atomic Card" optimizado
        lv_obj_set_style_pad_all(card, 8, 0);
    #else
        lv_obj_set_size(card, lv_pct(100), LV_SIZE_CONTENT);
        lv_obj_set_style_pad_all(card, 12, 0);
    #endif
    
    lv_obj_add_style(card, &style_card, 0);
    lv_obj_set_flex_flow(card, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(card, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_gap(card, 0, 0);

    // Lado Izquierdo: Info (65% del ancho para evitar overlap)
    lv_obj_t* info_cont = lv_obj_create(card);
    lv_obj_set_width(info_cont, lv_pct(65));
    lv_obj_set_height(info_cont, LV_SIZE_CONTENT);
    lv_obj_set_style_bg_opa(info_cont, 0, 0);
    lv_obj_set_style_border_width(info_cont, 0, 0);
    lv_obj_set_style_pad_all(info_cont, 0, 0);
    lv_obj_set_flex_flow(info_cont, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_style_pad_gap(info_cont, 4, 0);

    // Header: Solo el ID del Platillo
    lv_obj_t* meta_row = lv_obj_create(info_cont);
    lv_obj_set_size(meta_row, lv_pct(100), 16);
    lv_obj_set_style_bg_opa(meta_row, 0, 0);
    lv_obj_set_style_border_width(meta_row, 0, 0);
    lv_obj_set_style_pad_all(meta_row, 0, 0);
    lv_obj_set_flex_flow(meta_row, LV_FLEX_FLOW_ROW);
    lv_obj_set_style_pad_gap(meta_row, 6, 0);

    char id_buf[16]; 
    snprintf(id_buf, sizeof(id_buf), "#%d", dish.id);
    lv_obj_t* l_id = lv_label_create(meta_row);
    lv_label_set_text(l_id, id_buf);
    lv_obj_set_style_text_font(l_id, &lv_font_montserrat_12, 0);
    lv_obj_set_style_text_color(l_id, BS_COLOR_PRIMARY, 0);

    // Nombre del plato (Grandote)
    lv_obj_t* name_row = lv_obj_create(info_cont);
    lv_obj_set_size(name_row, lv_pct(100), LV_SIZE_CONTENT);
    lv_obj_set_style_bg_opa(name_row, 0, 0);
    lv_obj_set_style_border_width(name_row, 0, 0);
    lv_obj_set_style_pad_all(name_row, 0, 0);
    lv_obj_set_flex_flow(name_row, LV_FLEX_FLOW_ROW);
    lv_obj_set_style_pad_gap(name_row, 8, 0);

    char q_buf[8]; snprintf(q_buf, sizeof(q_buf), "%dx", dish.quantity);
    lv_obj_t* l_q = lv_label_create(name_row);
    lv_label_set_text(l_q, q_buf);
    lv_obj_set_style_text_font(l_q, &lv_font_montserrat_14, 0); // Boldish simulation
    lv_obj_set_style_text_color(l_q, BS_COLOR_PRIMARY, 0);

    lv_obj_t* l_name = lv_label_create(name_row);
    lv_label_set_text(l_name, dish.name.c_str());
    lv_obj_set_style_text_font(l_name, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(l_name, BS_COLOR_TEXT, 0);
    lv_label_set_long_mode(l_name, LV_LABEL_LONG_SCROLL_CIRCULAR);
    lv_obj_set_flex_grow(l_name, 1);

    // Complementos (Si existen)
    if (dish.is_modified && !dish.modification_notes.empty()) {
        lv_obj_t* mod_badge = lv_obj_create(info_cont);
        lv_obj_add_style(mod_badge, &style_mod_badge, 0);
        lv_obj_set_size(mod_badge, lv_pct(100), LV_SIZE_CONTENT);
        lv_obj_set_style_pad_all(mod_badge, 4, 0);
        
        lv_obj_t* l_mod = lv_label_create(mod_badge);
        lv_label_set_text(l_mod, (std::string(LV_SYMBOL_SETTINGS " ") + dish.modification_notes).c_str());
        lv_label_set_long_mode(l_mod, LV_LABEL_LONG_WRAP);
        lv_obj_set_width(l_mod, lv_pct(100));
    }

    // Lado Derecho: Estado (35% del ancho)
    lv_obj_t* status_area = lv_obj_create(card);
    #ifdef BS_LAYOUT_MODERN
        lv_obj_set_width(status_area, lv_pct(35));
    #else
        lv_obj_set_width(status_area, lv_pct(28));
    #endif
    lv_obj_set_height(status_area, LV_SIZE_CONTENT);
    lv_obj_set_style_bg_opa(status_area, 0, 0);
    lv_obj_set_style_border_width(status_area, 0, 0);
    lv_obj_set_style_pad_all(status_area, 0, 0);
    lv_obj_set_flex_flow(status_area, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_flex_align(status_area, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);

    lv_obj_t* s_cont = lv_obj_create(status_area);
    lv_obj_set_size(s_cont, 54, 26);
    lv_obj_set_style_radius(s_cont, 6, 0);
    lv_obj_set_style_border_width(s_cont, 1, 0);
    lv_obj_set_style_bg_opa(s_cont, 40, 0); // Fondo sutil del color de estado
    lv_obj_set_style_border_color(s_cont, status_to_color(dish.status), 0);
    lv_obj_set_style_bg_color(s_cont, status_to_color(dish.status), 0);
    
    lv_obj_t* s_lbl = lv_label_create(s_cont);
    lv_label_set_text(s_lbl, status_to_short(dish.status));
    lv_obj_set_style_text_font(s_lbl, &lv_font_montserrat_12, 0);
    lv_obj_set_style_text_color(s_lbl, status_to_color(dish.status), 0);
    lv_obj_center(s_lbl);

    lv_obj_t* dot = lv_obj_create(status_area);
    lv_obj_set_size(dot, 6, 6);
    lv_obj_set_style_radius(dot, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(dot, status_to_color(dish.status), 0);
    lv_obj_set_style_border_width(dot, 0, 0);
    lv_obj_set_style_pad_top(dot, 4, 0);

    // Registrar Widgets
    active_dish_cards[dish.id] = {card, s_lbl, s_cont, dot, order_id};

    return card;
}

void DashboardView::add_order(const char* title, const std::vector<DishItem>& items, int order_id) {
    if (!tablepad_cont) return;

    // Actualizar Header con info de la orden
    if (table_id_label) lv_label_set_text(table_id_label, title);
    if (order_id_label) {
        char buf[32];
        snprintf(buf, sizeof(buf), "ORD:%d", order_id);
        lv_label_set_text(order_id_label, buf);
    }

    for (const auto& item : items) {
        // Si ya existe borramos el previo
        if (active_dish_cards.count(item.id)) {
            lv_obj_del(active_dish_cards[item.id].card);
            active_dish_cards.erase(item.id);
        }
        
        lv_obj_t* card = create_dish_card(tablepad_cont, item, order_id, title);
        
        // Anim Entrada: Elástica (Overshoot)
        lv_obj_set_style_opa(card, 0, 0);
        lv_anim_t a;
        lv_anim_init(&a);
        lv_anim_set_var(&a, card);
        lv_anim_set_values(&a, 0, 255);
        lv_anim_set_duration(&a, BS_ANIM_DURATION);
        lv_anim_set_exec_cb(&a, anim_opa_cb);
        lv_anim_start(&a);

        lv_anim_set_values(&a, 10, 0); // Slide desde abajo sutil
        lv_anim_set_path_cb(&a, lv_anim_path_overshoot);
        lv_anim_set_exec_cb(&a, anim_y_cb);
        lv_anim_start(&a);
    }
}

void DashboardView::update_item_status(int order_id, int item_id, int /*progress*/, const char* status) {
    if (active_dish_cards.count(item_id)) {
        apply_item_state(active_dish_cards[item_id], status);
    }
}

void DashboardView::update_order_progress(int order_id, int /*percentage*/, const char* status) {
    for (auto& [item_id, w] : active_dish_cards) {
        if (w.order_id == order_id) {
            apply_item_state(w, status);
        }
    }
}

void DashboardView::apply_item_state(DishCardWidgets& w, const char* status) {
    std::string s(status);
    lv_color_t c = status_to_color(s);
    lv_label_set_text(w.status_label, status_to_short(s));
    lv_obj_set_style_text_color(w.status_label, c, 0);
    lv_obj_set_style_border_color(w.status_cont, c, 0);
    lv_obj_set_style_bg_color(w.dot, c, 0);
    
    if (s == "LISTO") {
        // Breathing Glow Animation (Glow suave que respira)
        lv_anim_t ag;
        lv_anim_init(&ag);
        lv_anim_set_var(&ag, w.card);
        lv_anim_set_values(&ag, BS_GLOW_OPA_MIN, BS_GLOW_OPA_MAX);
        lv_anim_set_duration(&ag, 1000);
        lv_anim_set_playback_duration(&ag, 1000);
        lv_anim_set_repeat_count(&ag, LV_ANIM_REPEAT_INFINITE);
        lv_anim_set_exec_cb(&ag, [](void* var, int32_t val) {
            lv_obj_set_style_shadow_opa((lv_obj_t*)var, (uint8_t)val, 0);
            lv_obj_set_style_shadow_color((lv_obj_t*)var, BS_COLOR_READY, 0);
            lv_obj_set_style_shadow_width((lv_obj_t*)var, 15 + (val / 15), 0);
        });
        lv_anim_start(&ag);
    } else {
        lv_anim_del(w.card, nullptr);
        lv_obj_set_style_shadow_color(w.card, lv_color_hex(0x000000), 0);
        lv_obj_set_style_shadow_opa(w.card, BS_SHADOW_OPA, 0);
        lv_obj_set_style_shadow_width(w.card, 25, 0);
    }
}

bool DashboardView::has_order(int order_id) {
    for (auto const& [item_id, w] : active_dish_cards) {
        if (w.order_id == order_id) return true;
    }
    return false;
}

void DashboardView::remove_order(int order_id) {
    std::vector<int> to_remove;
    for (auto const& [item_id, w] : active_dish_cards) {
        if (w.order_id == order_id) to_remove.push_back(item_id);
    }
    for (int id : to_remove) {
        remove_dish(id);
    }
}

void DashboardView::remove_dish(int item_id) {
    if (active_dish_cards.count(item_id)) {
        lv_obj_del(active_dish_cards[item_id].card);
        active_dish_cards.erase(item_id);
    }
}

void DashboardView::clear_orders() {
    for (auto const& [id, w] : active_dish_cards) {
        lv_obj_del(w.card);
    }
    active_dish_cards.clear();
}

void DashboardView::update_business_name(const std::string& name) {
    if (business_label) lv_label_set_text(business_label, name.c_str());
}

void DashboardView::update_table_id(const std::string& id) {
    if (table_id_label) lv_label_set_text(table_id_label, id.c_str());
}

void DashboardView::set_connection_status(int status) {
    if (!status_led) return;
    
    lv_color_t c = BS_COLOR_ERROR;
    if (status == 1) c = BS_COLOR_WARNING;
    if (status == 2) c = BS_COLOR_PRIMARY;
    
    lv_obj_set_style_bg_color(status_led, c, 0);
    lv_obj_set_style_shadow_color(status_led, c, 0);
}

void DashboardView::show_goodbye_screen() {
    if (goodbye_overlay) return;

    goodbye_overlay = lv_obj_create(screen);
    lv_obj_set_size(goodbye_overlay, lv_pct(100), lv_pct(100));
    lv_obj_set_style_bg_color(goodbye_overlay, BS_COLOR_BG, 0);
    lv_obj_set_style_bg_opa(goodbye_overlay, 230, 0);
    lv_obj_clear_flag(goodbye_overlay, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t* l = lv_label_create(goodbye_overlay);
    lv_label_set_text(l, LV_SYMBOL_OK "\nGRACIAS POR\nSU VISITA");
    lv_obj_set_style_text_align(l, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_style_text_font(l, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(l, BS_COLOR_PRIMARY, 0);
    lv_obj_center(l);

    // Animación de entrada
    lv_obj_set_style_opa(goodbye_overlay, 0, 0);
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, goodbye_overlay);
    lv_anim_set_values(&a, 0, 255);
    lv_anim_set_duration(&a, 500);
    lv_anim_set_exec_cb(&a, anim_opa_cb);
    lv_anim_start(&a);

    // Quitar el overlay de despedida después de 3 segundos
    lv_timer_t* t = lv_timer_create([](lv_timer_t* timer) {
        if (DashboardView::goodbye_overlay) {
            lv_obj_del(DashboardView::goodbye_overlay);
            DashboardView::goodbye_overlay = nullptr;
        }
    }, 3000, nullptr);
    
    lv_timer_set_repeat_count(t, 1);
}

void DashboardView::set_offline_mode(bool offline) {
    if (offline) {
        if (offline_cont) return;
        offline_cont = lv_obj_create(screen);
        lv_obj_set_size(offline_cont, lv_pct(100), lv_pct(100));
        lv_obj_set_style_bg_color(offline_cont, lv_color_hex(0x000000), 0);
        lv_obj_set_style_bg_opa(offline_cont, 180, 0);
        
        lv_obj_t* l = lv_label_create(offline_cont);
        lv_label_set_text(l, LV_SYMBOL_WARNING "\nOFFLINE");
        lv_obj_set_style_text_color(l, BS_COLOR_ERROR, 0);
        lv_obj_center(l);
    } else {
        if (offline_cont) {
            lv_obj_del(offline_cont);
            offline_cont = nullptr;
        }
    }
}

} // namespace UI
